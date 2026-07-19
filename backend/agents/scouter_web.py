import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import re
from urllib.parse import urlparse, unquote, parse_qs
from core.browser import init_stealth_browser
from database.engine import init_db, AsyncSessionLocal
from database.models import Lead
from services.status import set_status

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

EMAIL_REGEX = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
PHONE_REGEX = r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
BLACKLIST_DOMAINS = ["google.com", "facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com", "reddit.com", "amazon.com", "wikipedia.org"]
DIRECTORY_KEYWORDS = ["faculty", "directory", "people", "staff", "professor", "department", "member", "team"]
PROFILE_KEYWORDS = ["profile", "faculty", "people", "staff", "~"]

_current_query: str | None = None
_current_section_id = None

def _extract_url(href: str) -> str | None:
    if not href:
        return None
    if href.startswith("//"):
        qs = parse_qs(urlparse(href).query)
        decoded = qs.get("uddg", [None])[0]
        if decoded:
            href = unquote(decoded)
        else:
            href = "https:" + href
    if href.startswith("http") and not any(d in href for d in BLACKLIST_DOMAINS):
        return href
    return None

def _looks_like_person_name(text: str) -> bool:
    text = text.strip()
    if len(text.split()) < 2:
        return False
    title_indicators = ["prof.", "professor", "dr.", "dr ", "phd", "ph.d."]
    lower = text.lower()
    for t in title_indicators:
        if t in lower:
            return True
    common_words = {"home", "about", "contact", "search", "login", "register", "sign", "help", "faq", "blog", "news", "events", "research", "publications", "teaching", "awards", "students", "alumni", "admissions", "apply", "visit", "giving", "directory", "index"}
    words = set(w.lower() for w in text.split())
    if words & common_words:
        return False
    if len(text) > 60:
        return False
    return True

def _parse_emails(html: str) -> list[str]:
    found = list(set(re.findall(EMAIL_REGEX, html, re.I)))
    return [e for e in found if "example" not in e.lower() and ".png" not in e.lower() and ".jpg" not in e.lower() and "sentry" not in e.lower() and "wix" not in e.lower()]

def _parse_phones(html: str) -> list[str]:
    found = list(set(re.findall(PHONE_REGEX, html)))
    return [p.strip() for p in found if len(p.strip()) >= 10]

async def _search_ddg(page, query: str, max_results: int = 10) -> list[dict]:
    encoded = query.replace(" ", "+")
    await page.goto(f"https://html.duckduckgo.com/html/?q={encoded}", wait_until="domcontentloaded")
    await asyncio.sleep(2)
    items = page.locator("div.result")
    count = await items.count()
    results = []
    for i in range(min(count, max_results * 2)):
        try:
            item = items.nth(i)
            link = item.locator("a.result__a").first
            href = await link.get_attribute("href")
            title = await link.inner_text()
            snippet_el = item.locator("a.result__snippet").first
            snippet = await snippet_el.inner_text() if await snippet_el.count() > 0 else ""
            url = _extract_url(href)
            if url and title:
                results.append({"title": title.strip(), "href": url, "snippet": snippet.strip()})
        except:
            pass
        if len(results) >= max_results:
            break
    return results

async def _classify_page(page) -> str:
    try:
        url_lower = page.url.lower()
        title = (await page.title()).lower()
        text_sample = await page.evaluate("() => document.body.innerText.substring(0, 3000)")
        text_lower = text_sample.lower()[:2000]
        dir_score = sum(1 for k in DIRECTORY_KEYWORDS if k in url_lower or k in title)
        emails = _parse_emails(text_sample)
        lines = [l.strip() for l in text_sample.split("\n") if len(l.strip().split()) >= 2 and len(l.strip()) < 80]
        name_count = sum(1 for l in lines if _looks_like_person_name(l))
        has_list = await page.evaluate("() => document.querySelectorAll('ul, ol, table, [class*=list], [class*=grid]').length > 0")
        if dir_score >= 1:
            return "directory"
        if has_list and name_count >= 3:
            return "directory"
        if emails and name_count >= 1:
            return "directory"
        if name_count >= 1:
            return "single"
        return "article"
    except:
        return "article"

async def _extract_directory_entries(page) -> list[dict]:
    current_url = page.url.rstrip("/")
    js_links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a')).map(a => ({
            text: a.innerText.trim(),
            href: a.getAttribute('href')
        })).filter(x => x.text && x.href && x.text.split(' ').length >= 2 && x.text.length < 60)
    """)
    entries = []
    seen_hrefs = set()
    for link in js_links:
        text = link["text"]
        href = link["href"]
        if not _looks_like_person_name(text):
            continue
        if href.startswith("/"):
            href = current_url + href
        elif href.startswith("#"):
            continue
        if not href.startswith("http"):
            continue
        if href not in seen_hrefs:
            seen_hrefs.add(href)
            entries.append({"name": text, "href": href})
    entries = entries[:40]
    html = await page.content()
    emails = _parse_emails(html)
    known_names = {e["name"] for e in entries}
    for email in emails:
        entry_name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        if entry_name not in known_names:
            known_names.add(entry_name)
            entries.append({"name": entry_name, "email": email, "href": None})
    return entries

async def _extract_person_info(page, known_name: str | None = None) -> dict:
    info = {"name": known_name, "email": None, "phone": None, "description": None}
    try:
        h1 = page.locator("h1").first
        if await h1.count() > 0:
            name = (await h1.inner_text(timeout=2000)).strip()
            if name and len(name.split()) >= 2:
                info["name"] = name
    except:
        pass
    html = await page.content()
    emails = _parse_emails(html)
    if emails:
        info["email"] = emails[0]
    phones = _parse_phones(html)
    if phones:
        info["phone"] = phones[0]
    try:
        desc = await page.locator('meta[name="description"]').get_attribute("content", timeout=2000)
        if not desc:
            desc = await page.locator('meta[property="og:description"]').get_attribute("content", timeout=2000)
        if not desc:
            p = page.locator("p").first
            if await p.count() > 0:
                desc = (await p.inner_text(timeout=2000)).strip()[:300]
        if desc:
            info["description"] = desc.strip()[:500]
    except:
        pass
    return info

async def _save_lead(name: str, email: str | None, phone: str | None, description: str | None):
    if not name:
        return
    async with AsyncSessionLocal() as session:
        try:
            new_lead = Lead(
                name=name[:200],
                email=email,
                phone=phone,
                description=description,
                search_query=_current_query,
                section_id=_current_section_id,
            )
            session.add(new_lead)
            await session.commit()
            print(f"[Saved] {name} | Email: {email or 'N/A'} | Phone: {phone or 'N/A'}")
        except Exception:
            await session.rollback()

async def scout_web(query: str, depth: int = 5, section_id=None):
    global _current_query, _current_section_id
    _current_query = query
    _current_section_id = section_id
    await init_db()
    pages = await init_stealth_browser()
    page = pages["page"]
    max_profiles = min(depth, 20)

    try:
        set_status(True, f"Phase 1: Searching for '{query}'...", "scouting")
        print(f"\n{'='*60}")
        print(f"[*] Deep Research: \"{query}\"")
        print(f"{'='*60}")

        results = await _search_ddg(page, query, max_results=10)
        print(f"[*] Found {len(results)} search results")

        directory_queries = [
            f"{query} faculty directory",
            f"{query} staff list",
        ]
        for dq in directory_queries:
            extra = await _search_ddg(page, dq, max_results=8)
            existing_hrefs = {r["href"] for r in results}
            for r in extra:
                if r["href"] not in existing_hrefs:
                    results.append(r)
                    existing_hrefs.add(r["href"])
        print(f"[*] After directory queries: {len(results)} unique results")

        all_persons = []
        visited_dir_pages = set()
        visited_single_pages = set()
        persons_to_deep_scrape = []

        for idx, r in enumerate(results):
            if r["href"] in visited_dir_pages or r["href"] in visited_single_pages:
                continue
            set_status(True, f"Analyzing {r['title'][:35]} ({idx+1}/{len(results)})...", "scouting", idx + 1, len(results))
            try:
                await page.goto(r["href"], wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(1)
                if await _is_challenge_page(page):
                    print(f"[!] Challenge: {r['title'][:40]}")
                    continue
                classification = await _classify_page(page)
                print(f"[{classification}] {r['title'][:50]}")

                if classification == "directory":
                    visited_dir_pages.add(r["href"])
                    entries = await _extract_directory_entries(page)
                    print(f"  -> Found {len(entries)} potential entries")
                    for e in entries:
                        if e.get("email"):
                            all_persons.append(e)
                            await _save_lead(e["name"], e["email"], None, None)
                        elif e.get("href"):
                            persons_to_deep_scrape.append(e)
                elif classification == "single":
                    visited_single_pages.add(r["href"])
                    info = await _extract_person_info(page, r["title"])
                    if info["name"]:
                        all_persons.append(info)
                        await _save_lead(info["name"], info["email"], info["phone"], info["description"])
                else:
                    pass
            except Exception as e:
                print(f"[!] Error on {r['href']}: {e}")

        deep_count = min(len(persons_to_deep_scrape), max_profiles)
        if deep_count > 0:
            print(f"\n[*] Phase 2: Deep-scraping {deep_count} profile pages...")
            set_status(True, f"Deep-scraping {deep_count} profiles...", "scouting")
            for idx, p in enumerate(persons_to_deep_scrape[:deep_count]):
                set_status(True, f"Profile {p['name'][:30]} ({idx+1}/{deep_count})...", "scouting", idx + 1, deep_count)
                if p["href"] in visited_single_pages:
                    continue
                try:
                    await page.goto(p["href"], wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(1)
                    if await _is_challenge_page(page):
                        continue
                    visited_single_pages.add(p["href"])
                    info = await _extract_person_info(page, p["name"])
                    if info.get("email") or info.get("phone"):
                        all_persons.append(info)
                        await _save_lead(info["name"], info["email"], info["phone"], info["description"])
                except Exception as e:
                    print(f"[!] Deep scrape error {p['name']}: {e}")

        print(f"\n{'='*60}")
        print(f"[*] Research complete. Total leads: {len(all_persons)}")
        print(f"{'='*60}")

    except Exception as e:
        print(f"[!] Scout web error: {e}")
    finally:
        await pages["browser"].close()
        await pages["playwright"].stop()

if __name__ == "__main__":
    asyncio.run(scout_web("Computer Science professors at Stanford"))
