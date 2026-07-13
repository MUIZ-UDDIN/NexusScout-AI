from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import Lead
from core.browser import init_stealth_browser
import re
import asyncio

async def enrich_lead():
    EMAIL_REGEX = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
    BLACKLIST = ["sentry", "wix", "example", "vimeo", "google", "jpg", "png"]

    components = await init_stealth_browser()
    page = components["page"]
    browser = components["browser"]
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.status == "scouted").limit(10)
        leads = (await session.execute(stmt)).scalars().all()

        for lead in leads:
            if not lead.website or "http" not in lead.website: 
                continue
            try:
                await page.goto(lead.website, timeout=15000, wait_until="domcontentloaded")
                html = await page.content()
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

    await components["browser"].close()
    await components["playwright"].stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(enrich_lead())