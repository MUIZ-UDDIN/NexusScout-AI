import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.browser import init_stealth_browser
from database.engine import init_db, AsyncSessionLocal
from database.models import Lead
from services.status import set_status
import asyncio

_current_query: str | None = None
_current_section_id = None

async def scout_leads(query: str, depth: int = 3, section_id=None):
    global _current_query, _current_section_id
    _current_query = query
    _current_section_id = section_id
    await init_db()
    
    pages = await init_stealth_browser()

    try:
        page = pages["page"]
        encoded_query = query.replace(" ", "+")
        await page.goto(f"https://www.google.com/maps/search/{encoded_query}", wait_until="commit")


        print("[*] Waiting for results sidebar to appear...")
        try:
            first_link = page.locator("a[href*='/maps/place/']").first
            await first_link.wait_for(state="visible", timeout=30000)
            print("[✅] Success! Sidebar content captured.")

            await asyncio.sleep(2)

            print(f"[*] Scrolling to load more leads (depth={depth})...")
            set_status(True, f"Scrolling to load leads (depth={depth})...", "scouting")
            sidebar = page.locator("div[role='feed']")
            for s in range(depth):
                set_status(True, f"Scrolling ({s+1}/{depth})...", "scouting", s + 1, depth)
                await sidebar.evaluate("el => el.scrollBy(0, 4000)")
                await asyncio.sleep(2)

            business_cards = page.get_by_role("article")

            count = await business_cards.count()
            print(f"[*] Found {count} results in sidebar.")

            # First pass: collect card hrefs, skip ads
            card_hrefs = []
            for i in range(count):
                try:
                    card = business_cards.nth(i)
                    is_sponsored = await card.get_by_text("Sponsored").is_visible()
                    if is_sponsored:
                        print(f"[*] Skipping Ad at index {i}")
                        continue
                    link = card.locator("a").first
                    href = await link.get_attribute("href")
                    name = await link.get_attribute("aria-label")
                    if href and "/maps/place/" in href:
                        card_hrefs.append({"name": name, "href": href})
                except Exception as e:
                    print(f"[!] Error collecting card {i}: {e}")

            print(f"[*] Processing {len(card_hrefs)} non-sponsored leads...")
            set_status(True, f"Processing {len(card_hrefs)} leads...", "scouting")

            # Second pass: visit each place page to extract full data
            for idx, data in enumerate(card_hrefs):
                set_status(True, f"Scraping {data.get('name','?')} ({idx+1}/{len(card_hrefs)})...", "scouting", idx + 1, len(card_hrefs))
                try:
                    await page.goto(data["href"], wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2.5)

                    name_el = page.locator("h1").first
                    name = await name_el.inner_text() if await name_el.count() > 0 else data.get("name")

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

                    print(f"[Lead] {name} | Website: {website_url} | Phone: {phone} | Address: {address}")

                    if name:
                        async with AsyncSessionLocal() as session:
                            try:
                                new_lead = Lead(name=name, website=website_url, phone=phone, address=address, search_query=_current_query, section_id=_current_section_id)
                                session.add(new_lead)
                                await session.commit()
                                print(f"[💾] Saved to DB: {name}")
                            except Exception:
                                await session.rollback()
                                print(f"[⚠️] Duplicate skipped: {name}")

                except Exception as e:
                    print(f"[!] Error processing {data.get('name','?')}: {e}")
                    continue
       
        except Exception:
            print("[❌] Failed to find results sidebar even with direct navigation.")

    except Exception as e:
        print(f"An error occurred during scouting: {e}")

    finally:

        await pages["browser"].close()
        await pages["playwright"].stop()

if __name__ == "__main__":
    asyncio.run(scout_leads("Web Design Agencies in London"))