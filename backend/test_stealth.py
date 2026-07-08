from core.browser import init_stealth_browser
import asyncio

async def main():
    try:
        pages = await init_stealth_browser()
        page = pages["page"]
        await page.goto("https://bot.sannysoft.com/")
        await asyncio.sleep(5)

        await page.screenshot(path="screenshot.png")
    finally:
        # This code ALWAYS runs at the end
        await pages["browser"].close()
        await pages["playwright"].stop()

if __name__ == "__main__":
    asyncio.run(main())