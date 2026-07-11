from core.browser import init_stealth_browser
from database.engine import init_db, AsyncSessionLocal
from database.models import Lead
import asyncio

async def scout_leads(query: str):
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

            print("[*] Scrolling to load more leads...")
            sidebar = page.locator("div[role='feed']")
            for _ in range(3):
                await sidebar.evaluate("el => el.scrollBy(0, 4000)")
                await asyncio.sleep(2)

            business_cards = page.get_by_role("article")

            count = await business_cards.count()
            print(f"[*] Found {count} results in sidebar.")

            for i in range(count):
                try:
                    card = business_cards.nth(i)
                    is_sponsored = await card.get_by_text("Sponsored").is_visible()

                    if is_sponsored:
                        print(f"[*] Skipping Ad at index {i}")
                        continue

                    name_link = card.locator("a").first
                    name = await name_link.get_attribute("aria-label")  

                    website_link = card.locator('a[data-value="Website"]')

                    website_url = "Not Found"
                    if await website_link.count() > 0:
                        website_url = await website_link.get_attribute("href")

                    if name:
                        print(f"[Lead] {name} | Website: {website_url}")

                    async with AsyncSessionLocal() as session:
                        try:
                            new_lead = Lead(name=name, website=website_url)
                            session.add(new_lead)
                            await session.commit()
                            print(f"[💾] Saved to DB: {name}")

                        except Exception as e:
                            await session.rollback()
                            print(f"[⚠️] Duplicate skipped: {name}")

                except Exception as e:
                    print(f"[!] Error processing lead {i}: {e}")
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