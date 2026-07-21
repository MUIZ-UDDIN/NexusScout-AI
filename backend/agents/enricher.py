from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import Lead
from core.browser import init_stealth_browser
from services.status import set_status
import re
import asyncio
import httpx

N8N_CALLBACK_URL = "https://instance-analog-ebook-hair.trycloudflare.com/webhook-test/lead-enriched"

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
            stmt = select(Lead).where(Lead.status == "scouted").limit(10)
            leads = (await session.execute(stmt)).scalars().all()
            set_status(True, f"Enriching {len(leads)} leads...", "enriching", 0, len(leads))

            for idx, lead in enumerate(leads):
                set_status(True, f"Enriching {lead.name} ({idx+1}/{len(leads)})...", "enriching", idx + 1, len(leads))
                if not lead.website or "http" not in lead.website: 
                    continue
                try:
                    await page.goto(lead.website, timeout=10000, wait_until="domcontentloaded")
                    await asyncio.sleep(0.5)

                    if await _is_challenge_page(page):
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
                                continue
                            
                            new_html = await page.content()
                            new_found = re.findall(EMAIL_REGEX, new_html, re.I)
                            
                            clean_emails.extend([e for e in new_found if not any(noise in e.lower() for noise in BLACKLIST)])

                    clean_emails = list(set(clean_emails))

                    if clean_emails:
                        lead.email = ", ".join(clean_emails)
                        print(f"[✅] Final Leads for {lead.name}: {lead.email}")

                    lead.status = "enriched"
            
                except Exception:
                    lead.status = "failed"
                    print(f"[!] Could not reach {lead.website}")
                    continue
                
            await session.commit()
    finally:
        await components["browser"].close()
        await components["playwright"].stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(enrich_lead())