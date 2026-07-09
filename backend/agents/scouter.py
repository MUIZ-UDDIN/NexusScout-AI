from core.browser import init_stealth_browser
import asyncio


async def scout_leads(query: str):
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
            await page.screenshot(path="leads_found.png")
            
        except Exception:
            print("[❌] Failed to find results sidebar even with direct navigation.")
            await page.screenshot(path="failed_direct.png")

    except Exception as e:
        print(f"An error occurred during scouting: {e}")

    finally:

        await pages["browser"].close()
        await pages["playwright"].stop()

if __name__ == "__main__":
    asyncio.run(scout_leads("Web Design Agencies in London"))