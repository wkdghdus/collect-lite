# CollectLite — Agent Guide

Human-data collection and model-evaluation platform.
Stack: Next.js 14 · FastAPI · PostgreSQL 16 · Cohere

## Commands

- **Start all services:** `docker-compose up --build`
- **Frontend dev:** `cd frontend && npm run dev` (port 3000)
- **Backend dev:** `cd backend && uvicorn app.main:app --reload` (port 8000)
- **DB migrate:** `cd backend && alembic upgrade head`
- **Backend tests:** `cd backend && pytest tests/ -v`
- **Frontend type-check:** `cd frontend && npx tsc --noEmit`
- **Frontend build:** `cd frontend && npm run build`
- **Backend lint:** `cd backend && ruff check . && black --check .`

## Setup

```bash
cp .env.example .env   # then set COHERE_API_KEY
docker-compose up --build
```

## Directory Structure

- `frontend/` — Next.js App Router (annotator UI, admin, review, exports)
- `backend/` — FastAPI API + in-process background tasks
- `data/` — sample JSONL datasets for demo/seeding
- `docs/` — architecture diagram, API reference, demo script
- `docs/architecture/` — long-form architecture: `system-design.md` (component topology) and `process-flows.md` (per-flow writes/reads)
- `CLAUDE-PLANNING.md` — common misalignments in plannings. Things to consider when coming up with plan.

## Env Vars

See `.env.example`. Never commit `.env`.
Key: `DATABASE_URL`, `COHERE_API_KEY`, `SECRET_KEY`

## Implementation rules and guidelines

- Always keep every relevant CLAUDE.md files up to date to your implementation. 
- All tasks must be pushed to github. Commits are to follow conventional commit messages and to be separated by detailed task.