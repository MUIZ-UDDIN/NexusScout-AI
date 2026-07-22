from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import Lead
from core.browser import init_stealth_browser
from services.status import set_status
import re
import asyncio
import httpx

async def _search_emails_ddg(company: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(f"https://html.duckduckgo.com/html/?q={company.replace(' ', '+')}+email+contact")
            if r.status_code != 200:
                return []
            found = list(set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", r.text, re.I)))
            blacklist = ["sentry", "wix", "example", "vimeo", "google", "jpg", "png"]
            clean = [e for e in found if not any(noise in e.lower() for noise in blacklist)]
            company_key = company.split()[0].lower()
            return [e for e in clean if company_key in e.lower().split("@")[1] or company_key in e.lower().split("@")[0]]
    except Exception:
        return []

CHALLENGE_TITLE_PATTERNS = [
    "verifying you are human", "verifying you're human",
    "just a moment", "attention required", "please wait",
    "security check", "challenge", "cloudflare",
]
CHALLENGE_BODY_PATTERNS = [
    "cloudflare", "turnstile", "cf-challenge",
    "verify you are human", "security check",
]

async def _is_challenge_page(page) -> bool:
    try:
        title = await page.title()
        title_lower = title.lower()
        for p in CHALLENGE_TITLE_PATTERNS:
            if p in title_lower:
                return True
        body_text = await page.locator("body").inner_text(timeout=3000)
        body_lower = body_text.lower()[:500]
        for p in CHALLENGE_BODY_PATTERNS:
            if p in body_lower:
                return True
    except Exception:
        pass
    return False

async def enrich_lead():
    EMAIL_REGEX = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
    BLACKLIST = ["sentry", "wix", "example", "vimeo", "google", "jpg", "png"]

    try:
        components = await init_stealth_browser()
    except Exception as e:
        print(f"[!] Enrichment browser failed to launch: {e}")
        return

    page = components["page"]
    browser = components["browser"]
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Lead).where(Lead.status == "scouted")
            leads = (await session.execute(stmt)).scalars().all()
            set_status(True, f"Enriching {len(leads)} leads...", "enriching", 0, len(leads))

            for idx, lead in enumerate(leads):
                set_status(True, f"Enriching {lead.name} ({idx+1}/{len(leads)})...", "enriching", idx + 1, len(leads))
                has_maps_data = bool(lead.phone or lead.address)
                got_site_data = False

                if not lead.website or "http" not in lead.website:
                    if has_maps_data:
                        lead.status = "enriched"
                        print(f"[✓] {lead.name} enriched from Maps data (no website)")
                        continue
                    lead.status = "failed"
                    print(f"[!] No valid website for {lead.name}, marking failed")
                    continue
                try:
                    await page.goto(lead.website, timeout=10000, wait_until="domcontentloaded")
                    await asyncio.sleep(0.5)

                    got_site_data = True

                    if await _is_challenge_page(page):
                        if has_maps_data or got_site_data:
                            lead.status = "enriched"
                            print(f"[✓] {lead.name} enriched (challenge page but site exists)")
                            continue
                        print(f"[!] Challenge page, marking failed: {lead.website}")
                        lead.status = "failed"
                        continue

                    html = await page.content()

                    desc = None
                    try:
                        desc = await page.locator('meta[name="description"]').get_attribute("content", timeout=3000)
                    except:
                        pass
                    if not desc:
                        try:
                            desc = await page.locator('meta[property="og:description"]').get_attribute("content", timeout=3000)
                        except:
                            pass
                    if not desc:
                        try:
                            p = page.locator("p").first
                            if await p.count() > 0:
                                desc = (await p.inner_text(timeout=3000)).strip()[:300]
                        except:
                            pass
                    if desc:
                        lead.description = desc.strip()[:500]

                    found = list(set(re.findall(EMAIL_REGEX, html, re.I)))
                    clean_emails = [e for e in found if not any(noise in e.lower() for noise in BLACKLIST)]

                    if not clean_emails:
                        contact_link = page.get_by_role("link", name=re.compile(r"contact|about|touch", re.I)).first

                        if await contact_link.count() > 0:
                            print(f"[*] Homepage empty. Diving into: {await contact_link.get_attribute('href')}")
                            await contact_link.click()
                            try:
                                await page.wait_for_load_state("domcontentloaded")

                            except Exception:
                                lead.status = "enriched"
                                print(f"[✓] {lead.name} enriched (contact page failed, homepage data saved)")
                                continue
                            
                            new_html = await page.content()
                            new_found = re.findall(EMAIL_REGEX, new_html, re.I)
                            
                            clean_emails.extend([e for e in new_found if not any(noise in e.lower() for noise in BLACKLIST)])

                    clean_emails = list(set(clean_emails))

                    if not clean_emails:
                        print(f"[*] No email on page, searching DuckDuckGo for {lead.name}...")
                        ddg_emails = await _search_emails_ddg(lead.name)
                        if ddg_emails:
                            clean_emails = ddg_emails[:3]
                            print(f"[✅] Found emails via DDG: {clean_emails}")

                    if clean_emails:
                        lead.email = ", ".join(clean_emails)
                        print(f"[✅] Final Leads for {lead.name}: {lead.email}")

                    lead.status = "enriched"

                except Exception:
                    if has_maps_data or got_site_data:
                        lead.status = "enriched"
                        print(f"[✓] {lead.name} enriched (website partially loaded)")
                        continue
                    print(f"[!] Could not reach {lead.website}, marking failed")
                    lead.status = "failed"
                    continue
                
            await session.commit()
    finally:
        await components["browser"].close()
        await components["playwright"].stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(enrich_lead())