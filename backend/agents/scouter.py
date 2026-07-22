import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import re
from core.browser import init_stealth_browser
from database.engine import init_db, AsyncSessionLocal
from database.models import Lead
from services.status import set_status
import asyncio

_current_query: str | None = None
_current_section_id = None
_current_headline: str | None = None


SUFFIXES = {"ltd", "ltd.", "limited", "inc", "inc.", "llc", "gmbh", "co", "co.", "corp", "corp.",
            "group", "technologies", "tech", "solutions", "llp", "plc",
            "usa", "uk", "eu", "asia", "germany", "france", "india", "china", "japan",
            "gmbh & co", "kg", "sa", "bv", "nv", "pty", "pvt", "pvt."}


def _matches_exact(name: str | None, query: str) -> bool:
    if not name:
        return False
    name_clean = name.strip().lower()
    query_clean = query.strip().lower()

    if name_clean == query_clean:
        return True
    if name_clean.startswith(query_clean):
        rest = name_clean[len(query_clean):].strip().strip(",").strip()
        if not rest:
            return True
        words = [w for w in rest.split() if w]
        return all(w in SUFFIXES for w in words)
    return False

async def _extract_details(page, known_name: str | None = None) -> dict:
    name_el = page.locator("h1").first
    name = await name_el.inner_text(timeout=3000) if await name_el.count() > 0 else known_name

    phone = None
    phone_el = page.locator('button[data-item-id*="phone:tel:"]').first
    if await phone_el.count() > 0:
        raw = await phone_el.get_attribute("data-item-id")
        if raw:
            phone = raw.split("phone:tel:")[-1]

    website_url = None
    for sel in ['a[data-item-id="website"]', 'a[href*="://"][data-item-id*="website"]', '[data-tooltip*="website"] a', 'a[aria-label*="Website"]']:
        el = page.locator(sel).first
        if await el.count() > 0:
            href = await el.get_attribute("href")
            if href and href != "#" and href.startswith("http"):
                website_url = href
                break
    if not website_url:
        try:
            website_link = page.get_by_role("link", name="Website").first
            if await website_link.count() > 0:
                href = await website_link.get_attribute("href")
                if href and href != "#" and href.startswith("http"):
                    website_url = href
        except:
            pass

    address = None
    addr_el = page.locator('button[data-item-id*="address"]').first
    if await addr_el.count() > 0:
        address = await addr_el.get_attribute("aria-label")

    return {"name": name, "website": website_url, "phone": phone, "address": address}


async def _save_lead(name: str, website: str | None, phone: str | None, address: str | None):
    if not name:
        return
    if not _matches_exact(name, _current_query):
        print(f"[!] SKIP {name} — doesn't match query '{_current_query}'")
        return
    async with AsyncSessionLocal() as session:
        try:
            new_lead = Lead(
                name=name[:200],
                website=website,
                phone=phone,
                address=address,
                search_query=_current_query,
                section_id=_current_section_id,
                trigger_event=_current_headline,
            )
            session.add(new_lead)
            await session.commit()
            print(f"[Saved] {name} | Website: {website or 'N/A'}")
        except Exception:
            await session.rollback()
            print(f"[Duplicate] {name}")


async def scout_leads(query: str, depth: int = 3, section_id=None, headline=None):
    global _current_query, _current_section_id, _current_headline
    _current_query = query
    _current_section_id = section_id
    _current_headline = headline
    await init_db()

    pages = await init_stealth_browser()
    page = pages["page"]

    try:
        encoded_query = query.replace(" ", "+")
        await page.goto(f"https://www.google.com/maps/search/{encoded_query}", wait_until="commit")

        print("[*] Waiting for UI to resolve...")
        feed_locator = page.locator("div[role='feed']")

        try:
            await page.wait_for_selector("div[role='feed'], a[data-item-id='website']", timeout=20000)
        except Exception:
            pass

        await asyncio.sleep(2)

        # ── Check current URL for direct place redirect ──
        current_url = page.url

        # ── CASE A: List mode (feed with multiple results) ──
        if await feed_locator.is_visible():
            print("[List Mode] Processing multiple results...")
            set_status(True, "Scrolling to load leads...", "scouting")
            for s in range(depth):
                set_status(True, f"Scrolling ({s+1}/{depth})...", "scouting", s + 1, depth)
                await feed_locator.evaluate("el => el.scrollBy(0, 4000)")
                await asyncio.sleep(2)

            business_cards = feed_locator.get_by_role("article") if await feed_locator.count() > 0 else page.get_by_role("article")
            count = await business_cards.count()
            print(f"[*] Found {count} article elements on page.")

            card_hrefs = []
            skipped_sponsored = 0
            skipped_no_place = 0
            for i in range(count):
                try:
                    card = business_cards.nth(i)
                    sponsored = card.get_by_text("Sponsored")
                    is_sponsored = await sponsored.count() > 0 and await sponsored.first.is_visible()
                    if is_sponsored:
                        skipped_sponsored += 1
                        continue
                    link = card.locator("a").first
                    if await link.count() == 0:
                        skipped_no_place += 1
                        continue
                    href = await link.get_attribute("href")
                    name = await link.get_attribute("aria-label")
                    if href and "/maps/place/" in href:
                        card_hrefs.append({"name": name, "href": href})
                    else:
                        skipped_no_place += 1
                except Exception as e:
                    print(f"[!] Error collecting card {i}: {e}")

            print(f"[*] Sidebar: {skipped_sponsored} sponsored, {skipped_no_place} non-place, {len(card_hrefs)} valid cards")

            exact_hrefs = [c for c in card_hrefs if _matches_exact(c.get("name"), query)]
            skipped_name = len(card_hrefs) - len(exact_hrefs)
            card_hrefs = exact_hrefs
            print(f"[*] {skipped_name} cards skipped (name doesn't match), {len(card_hrefs)} kept")
            set_status(True, f"Processing {len(card_hrefs)} leads...", "scouting")

            for idx, data in enumerate(card_hrefs):
                set_status(True, f"Scraping {data.get('name','?')} ({idx+1}/{len(card_hrefs)})...", "scouting", idx + 1, len(card_hrefs))
                try:
                    await page.goto(data["href"], wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2)
                    details = await _extract_details(page, data.get("name"))
                    await _save_lead(details["name"], details["website"], details["phone"], details["address"])
                except Exception as e:
                    print(f"[!] Error processing {data.get('name','?')}: {e}")

        # ── CASE B: Single mode (direct business profile) ──
        elif "/maps/place/" in current_url or await page.locator('a[data-item-id="website"]').count() > 0:
            print("[Single Mode] Direct business profile found...")
            details = await _extract_details(page, query)
            print(f"[Lead] {details['name']} | Website: {details['website']} | Phone: {details['phone']}")
            await _save_lead(details["name"], details["website"], details["phone"], details["address"])

        else:
            print("[!] No results found for this query.")

    except Exception as e:
        print(f"An error occurred during scouting: {e}")

    finally:
        await pages["browser"].close()
        await pages["playwright"].stop()

if __name__ == "__main__":
    asyncio.run(scout_leads("Web Design Agencies in London"))