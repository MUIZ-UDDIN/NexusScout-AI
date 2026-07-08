from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from .config import *
import asyncio

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

    await stealth_async(context)
    page = await context.new_page()

    return {
        "playwright": playwright,
        "browser": browser,
        "context": context,
        "page": page
    }
    