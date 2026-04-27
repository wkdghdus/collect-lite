# CollectLite

A full-stack human-data collection and model-evaluation platform. Implements annotation project management, dataset ingestion, model-in-the-loop pre-labeling, annotator work queues, consensus and review workflows, quality dashboards, and dataset export.

Built with Next.js · TypeScript · React · FastAPI · PostgreSQL · Cohere

## Quick Start (Docker Compose)

```bash
cp .env.example .env
# Edit .env and add your COHERE_API_KEY
docker-compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

## Manual Dev Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Next.js, TypeScript, React, Tailwind CSS, shadcn/ui, TanStack Query, Recharts, Zod |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic, psycopg3 |
| AI / Model-in-loop | Cohere Rerank, Cohere Embed, SentenceTransformers |
| Database | PostgreSQL 16 |
| Queue | Redis |
| DevOps | Docker Compose, GitHub Actions |

## Project Structure

```
collect-lite/
  frontend/        Next.js app (annotator + admin UI)
  backend/         FastAPI service + background workers
  data/            Sample JSONL datasets for demo
  docs/            Architecture, API reference, demo script
```

See `system-design.md` for full architecture and data model.
