import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uuid
from datetime import datetime
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from database.engine import AsyncSessionLocal, init_db
from database.models import Lead, Section
from agents.scouter import scout_leads
from agents.scouter_web import scout_web
from agents.enricher import enrich_lead
from services.status import set_status, get_status
from services.ai_service import generate_opening
from services.email_service import send_lead_email
import re
from pydantic import BaseModel
import asyncio

class ScoutRequest(BaseModel):
    query: str
    depth: int = 3
    section_id: str | None = None
    mode: str = "maps"
    headline: str | None = None

class N8NScoutRequest(BaseModel):
    company: str
    score: str | int = 0
    headline: str


def company_matches_headline(company: str, headline: str | None) -> bool:
    if not headline:
        return False
    pattern = re.escape(company)
    return bool(re.search(rf"(?<!\w){pattern}(?!\w)", headline, re.IGNORECASE))


def clean_company_name(name: str) -> str:
    name = re.sub(r'\.[a-zA-Z]{2,}$', '', name.strip())
    return name.strip()


def extract_url_from_headline(headline: str) -> str | None:
    body = headline.split(" - ")[0] if " - " in headline else headline
    url = re.search(r'https?://[^\s\)]+', body)
    if url:
        return url.group(0)
    domain = re.search(r'(?<!\w)([a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.(?:com|io|ai|co|net|org|app|dev|in|uk|us|eu))(?!\S)', body)
    if domain:
        return domain.group(0)
    return None

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

scout_lock = asyncio.Semaphore(1)

async def run_full_research(query: str, depth: int = 3, section_id: str | None = None, mode: str = "maps", headline: str | None = None):
    async with scout_lock:
        try:
            set_status(True, "Launching browser...", "scouting")
            async with AsyncSessionLocal() as session:
                if section_id:
                    section = await session.get(Section, uuid.UUID(section_id))
                    if section:
                        section.name = query
                        section.search_query = query
                else:
                    existing = await session.execute(
                        select(Section).where(Section.search_query == query)
                    )
                    section = existing.scalar_one_or_none()
                    if not section:
                        section = Section(name=query, search_query=query)
                        session.add(section)
                await session.commit()
                await session.refresh(section)
            if mode == "web":
                await scout_web(query, depth=depth, section_id=section.id, headline=headline)
            else:
                await scout_leads(query, depth=depth, section_id=section.id, headline=headline)
            set_status(True, "Enriching leads...", "enriching")
            await enrich_lead()
        except Exception as e:
            print(f"[!] run_full_research failed: {e}")
        finally:
            set_status(False, "Done", "done")

@app.get("/api/scout/status")
async def scout_status():
    return get_status()

N8N_SECTION_NAME = "N8N Scout"


async def run_n8n_research(company: str, headline: str | None):
    async with scout_lock:
        try:
            set_status(True, f"n8n: Scouting {company}...", "scouting")
            async with AsyncSessionLocal() as session:
                existing = await session.execute(
                    select(Section).where(Section.name == N8N_SECTION_NAME)
                )
                section = existing.scalar_one_or_none()
                if not section:
                    section = Section(name=N8N_SECTION_NAME, search_query=N8N_SECTION_NAME)
                    session.add(section)
                    await session.commit()
                    await session.refresh(section)

            await scout_leads(company, depth=3, section_id=section.id, headline=headline)

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(func.count()).select_from(Lead).where(Lead.section_id == section.id, Lead.name == company)
                )
                maps_found = result.scalar() or 0

            if maps_found == 0:
                print(f"[n8n] No Maps results for {company}, falling back to web search...")
                set_status(True, f"n8n: Web fallback for {company}...", "scouting")
                await scout_web(company, depth=3, section_id=section.id, headline=headline, company_mode=True)

            set_status(True, "Enriching leads...", "enriching")
            await enrich_lead()
        except Exception as e:
            print(f"[!] run_n8n_research failed: {e}")
        finally:
            set_status(False, "Done", "done")


@app.post("/api/scout/n8n")
async def trigger_n8n_scout(req: Request, background_tasks: BackgroundTasks):
    try:
        body = await req.json()
    except Exception:
        form = await req.form()
        body = {k: v for k, v in form.items()}

    company = body.get("company") or body.get("query", "")
    score = body.get("score", 0)
    headline = body.get("headline", "")

    if not company or not headline:
        print(f"[n8n] Missing fields: {body}")
        return {"status": "Error", "reason": "Missing company/query or headline"}

    print(f"[n8n] Received: company='{company}' score='{score}' headline='{headline[:80]}...'")

    if not company_matches_headline(company, headline):
        print(f"[n8n] SKIPPED {company} — not found in headline")
        return {"status": "Skipped", "reason": "Company name not found in headline", "company": company}

    company_clean = clean_company_name(company)
    print(f"[n8n] Scouting {company_clean} (original: {company})")

    set_status(True, f"n8n: Queued {company_clean}...", "queued")
    background_tasks.add_task(run_n8n_research, company_clean, headline)
    return {"status": "Agent Dispatched", "company": company_clean, "headline": headline}

@app.post("/api/scout")
async def trigger_scout(request: ScoutRequest, background_tasks: BackgroundTasks):
    set_status(True, "Queued...", "queued")
    background_tasks.add_task(run_full_research, request.query, request.depth, request.section_id, request.mode, request.headline)
    return {"status": "Agent Dispatched", "job": request.query}

@app.get("/api/leads")
async def get_leads(section_id: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if section_id:
        stmt = stmt.where(Lead.section_id == uuid.UUID(section_id))
    results = await db.execute(stmt)

    return results.scalars().all()

@app.get("/api/leads/unposted")
async def get_unposted_leads(db: AsyncSession = Depends(get_db)):
    stmt = select(Lead).where(Lead.posted == False, Lead.status == "enriched").order_by(Lead.created_at.desc())
    results = await db.execute(stmt)
    return results.scalars().all()

class MarkPostedRequest(BaseModel):
    lead_ids: list[str]

@app.post("/api/leads/mark-posted")
async def mark_leads_posted(body: MarkPostedRequest, db: AsyncSession = Depends(get_db)):
    for lid in body.lead_ids:
        lead = await db.get(Lead, uuid.UUID(lid))
        if lead and not lead.posted:
            lead.posted = True
            print(f"[✓] Marked posted: {lead.name} ({lead.email})")
    await db.commit()
    return {"status": "ok", "count": len(body.lead_ids)}

@app.get("/api/leads/stats")
async def get_lead_stats(section_id: str | None = None, db: AsyncSession = Depends(get_db)):
    base = select(Lead)
    if section_id:
        base = base.where(Lead.section_id == uuid.UUID(section_id))

    total = await db.execute(select(func.count()).select_from(base.subquery()))
    enriched = await db.execute(
        select(func.count()).select_from(base.where(Lead.status == "enriched").subquery())
    )
    failed = await db.execute(
        select(func.count()).select_from(base.where(Lead.status == "failed").subquery())
    )

    return {
        "total": total.scalar(),
        "enriched": enriched.scalar(),
        "failed": failed.scalar(),
    }

@app.post("/api/leads/{lead_id}/contact")
async def contact_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, uuid.UUID(lead_id))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    opening = generate_opening(lead.name)
    result = send_lead_email(lead.email, lead.name, opening)
    now = datetime.now()
    lead.status = "contacted"
    lead.contacted_at = now
    await db.commit()
    return {"status": "contacted", "email_result": result}

@app.get("/api/sections")
async def get_sections(db: AsyncSession = Depends(get_db)):
    stmt = select(Section).order_by(Section.created_at.desc())
    results = await db.execute(stmt)
    sections = results.scalars().all()
    out = []
    for s in sections:
        cnt = await db.execute(
            select(func.count()).select_from(Lead).where(Lead.section_id == s.id)
        )
        out.append({"id": str(s.id), "name": s.name, "search_query": s.search_query, "lead_count": cnt.scalar()})
    return out

@app.post("/api/sections")
async def create_section(db: AsyncSession = Depends(get_db)):
    s = Section(name="New Tab", search_query=None)
    db.add(s)
    await db.commit()
    return {"id": str(s.id), "name": s.name, "search_query": s.search_query, "lead_count": 0}

class RenameSection(BaseModel):
    name: str

@app.put("/api/sections/{section_id}")
async def rename_section(section_id: str, body: RenameSection, db: AsyncSession = Depends(get_db)):
    s = await db.get(Section, uuid.UUID(section_id))
    if not s:
        raise HTTPException(404, "Section not found")
    s.name = body.name
    await db.commit()
    return {"status": "renamed"}

@app.delete("/api/sections/{section_id}")
async def delete_section(section_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(Section, uuid.UUID(section_id))
    if not s:
        raise HTTPException(404, "Section not found")
    leads = await db.execute(select(Lead).where(Lead.section_id == s.id))
    for lead in leads.scalars().all():
        await db.delete(lead)
    await db.delete(s)
    await db.commit()
    return {"status": "deleted"}

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, uuid.UUID(lead_id))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"status": "deleted"}
