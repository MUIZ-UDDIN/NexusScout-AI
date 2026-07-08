from core.browser import init_stealth_browser
import asyncio


async def scout_leads(query: str):
    pages = await init_stealth_browser()

    try:
        page = pages["page"]
        await page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
        try:
            await page.get_by_text("Accept all").click(timeout=5000)

        except:
            pass 

        search_box = page.get_by_role("combobox", name="Search Google Maps")
        await search_box.wait_for(state="visible", timeout=10000)
        await search_box.click()

        await search_box.press_sequentially(query, delay=100)
        await asyncio.sleep(1)

        await page.get_by_label("Search", exact=True).click()
        await page.keyboard.press("Enter") 
        print(f"[*] Waiting for results sidebar: 'Results for {query}'")

        print("[*] Waiting for results to load...")
        try:
            # We look for the universal link pattern '/maps/place/'
            first_link = page.locator("a[href*='/maps/place/']").first
            await first_link.wait_for(state="visible", timeout=15000)
            print("[✅] Search successful! Results are visible.")
        except:
            print("[❌] Timeout: Results sidebar did not appear.")
            await page.screenshot(path="debug_timeout.png")
            return
        

        await asyncio.sleep(5)

        await page.screenshot(path="test.png")
        print("Search successful! Screenshot saved.")

    except Exception as e:
        print(f"An error occurred during scouting: {e}")

    finally:

        await pages["browser"].close()
        await pages["playwright"].stop()

if __name__ == "__main__":
    asyncio.run(scout_leads("Web Design Agencies in London"))