from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from .config import *

async def init_stealth_browser():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO
        )

    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport=VIEWPORT,
        locale=LOCALE
        )

    page = await context.new_page()
    stealth = Stealth()
    await stealth.apply_stealth_async(page)

    return {
        "playwright": playwright,
        "browser": browser,
        "context": context,
        "page": page
    }
    