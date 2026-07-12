from sqlalchemy import select
from database.engine import AsyncSessionLocal
from database.models import Lead
from core.browser import init_stealth_browser
import re
import asyncio

async def enrich_lead():
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
                found = list(set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", html, re.I)))

                if found:
                    lead.email = ", ".join(found)
                    print(f"[✅] Found: {lead.email}")

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