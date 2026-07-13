import uuid
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from database.engine import AsyncSessionLocal
from database.models import Lead
from agents.scouter import scout_leads

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/scout")
async def trigger_scout(query: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(scout_leads, query)
    return {"status": "Agent Dispatched"}

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.get("/api/leads")
async def get_leads(db: AsyncSession = Depends(get_db)):
    stmt = select(Lead).order_by(Lead.created_at.desc())
    results = await db.execute(stmt)

    return results.scalars().all()

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == uuid.UUID(lead_id)))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"status": "deleted"}
