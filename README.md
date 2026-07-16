# NexusScout AI — Autonomous Lead Generation Engine

A three-agent AI pipeline that scrapes Google Maps, enriches business data, and sends personalized outreach emails — all from a web UI.

## Architecture

```
User (React UI)
    │
    ▼
FastAPI Backend
    │
    ├── /api/scout       → Agent 1: Scouter (Playwright + Stealth)
    ├── /api/leads       → Agent 2: Enricher (Email extraction)
    ├── /api/leads/contact → Agent 3: Outreach (Groq + Resend)
    │
    └── SQLite Database (leads.db)
```

### Three-Agent Pipeline

| Agent | File | Role |
|---|---|---|
| **Scouter** | `backend/agents/scouter.py` | Launches a stealth Playwright browser, searches Google Maps, extracts business names and websites |
| **Enricher** | `backend/agents/enricher.py` | Visits each website, scrapes contact emails, categorizes leads |
| **Outreach** | `backend/services/ai_service.py` + `email_service.py` | Uses Groq LLM to write personalized opening lines, sends emails via Resend |

### Tech Stack

- **Frontend**: Next.js 16 + Tailwind CSS (dark theme)
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite
- **Automation**: Playwright + playwright-stealth
- **AI**: Groq (Llama 3.3 70B) for email personalization
- **Email**: Resend API for delivery

## Quick Start

```bash
# Backend
cd backend
uv add .          # install dependencies
uv run uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Required API Keys

Add to `backend/.env`:

```
GROQ_API_KEY=your_key
RESEND_API_KEY=your_key
```

## UI Features

- **Stats Bar**: Real-time counts (Total / Enriched / Failed)
- **Search Bar**: Type a query → Scouter scrapes Google Maps
- **Lead Cards**: Expandable details, email, website, status badges
- **Contact Button**: Triggers AI personalization + email delivery
- **Delete**: Remove leads with one click

## Portfolio Demo

1. Open `http://localhost:3000`
2. Type "Web Design Agencies in London" → click Scout
3. Wait for results → click a lead to expand
4. Click Contact → check your inbox for the AI-generated email
