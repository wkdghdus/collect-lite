# System Design — CollectLite

> Last verified against commit: **47cda7f**

This doc is the **static topology** view of CollectLite: every runtime component, the wires between them, and what each wire carries. It is the source for the *system-design* Excalidraw diagram. For per-process flows and what each flow writes, see [`process-flows.md`](./process-flows.md).

> Components present in the repository but not yet wired into application code are intentionally omitted from this topology. The doc reflects what is **actually running and exchanging data** as of the verification commit at the top of this file.

---

## 1. Runtime components

| Name | Role | Source / proof | Port | How it starts |
|---|---|---|---|---|
| **Next.js frontend** | Annotator + admin + review + export UI | `frontend/src/app/` (App Router pages), `frontend/src/lib/api.ts` (HTTP client) | 3000 | `docker-compose up` builds `./frontend/Dockerfile`; locally `cd frontend && npm run dev` |
| **FastAPI backend** | REST API for every business operation | `backend/app/main.py` mounts 10 routers under `/api`; `backend/app/db.py:8` engine | 8000 | `backend/entrypoint.sh` runs `alembic upgrade head` then `uvicorn app.main:app` |
| **In-process BackgroundTasks** | Async work runner — **lives inside the FastAPI process**, not a separate container | `backend/app/workers/jobs.py` (5 jobs); routers call `BackgroundTasks.add_task(...)` | — | Same process / container as FastAPI |
| **PostgreSQL 16** | Source of truth for every persistent record | `docker-compose.yml` `postgres` service; `postgres:16-alpine` | 5432 | `docker-compose up`, named volume `postgres_data` |
| **Alembic** | Schema migration runner — **one-shot at backend startup**, not a service | `backend/alembic/`, `backend/alembic.ini`, `backend/entrypoint.sh` | — | `alembic upgrade head` runs once before uvicorn |
| **Cohere Rerank API** | External rerank model used to generate model suggestions | `backend/app/services/cohere_service.py:23` (`generate_rerank_suggestion`) | HTTPS | Hit synchronously from the request thread when `COHERE_API_KEY` is set |

The FastAPI backend hosts 10 routers (`backend/app/main.py:56-65`): `projects`, `datasets`, `tasks`, `annotations`, `suggestions`, `consensus`, `reviews`, `metrics`, `exports`, `users`. The 5 background jobs (`backend/app/workers/jobs.py`) are: `generate_tasks`, `compute_consensus`, `create_export`, `run_model_suggestions` (stub), `refresh_metrics` (stub).

---

## 2. Communication topology

Every edge in the running system. Each row is one arrow on the diagram.

| # | Source | Target | Protocol | Purpose | Code reference |
|---|---|---|---|---|---|
| 1 | Browser | Next.js frontend | HTTP (3000) | Page navigation, SSR + CSR render | `frontend/src/app/` |
| 2 | Next.js frontend | FastAPI backend | HTTP/REST JSON (8000) | All API calls go through `api.get/post/patch` (typed `fetch` wrapper) | `frontend/src/lib/api.ts` |
| 3 | FastAPI router | PostgreSQL | SQL (SQLAlchemy sync via psycopg3) | All reads/writes through `get_db()` dependency | `backend/app/db.py:8` |
| 4 | FastAPI router | BackgroundTasks (in-process) | Python function call | Schedule async work after returning the response | `backend/app/routers/tasks.py:137`, `backend/app/routers/annotations.py:125`, `backend/app/routers/exports.py:46` |
| 5 | BackgroundTask | PostgreSQL | SQL | Each job opens its own `SessionLocal()` and writes results | `backend/app/workers/jobs.py:9-16` |
| 6 | BackgroundTask `create_export` | Filesystem | File write | Writes JSONL/CSV to `EXPORTS_DIR/{export_id}.{format}` | `backend/app/services/export.py:167-188` |
| 7 | FastAPI `download_export` | Filesystem | File read (`FileResponse`) | Streams the export file back to the browser | `backend/app/routers/exports.py:77` |
| 8 | FastAPI `create_task_suggestion` | Cohere API | HTTPS (cohere SDK) | **Synchronous, inline** rerank call; falls back to local Jaccard when key is unset | `backend/app/services/cohere_service.py:23`, fallback at `backend/app/services/model_suggestions.py:53` |
| 9 | Alembic (one-shot) | PostgreSQL | SQL DDL | Apply pending migrations on container boot | `backend/alembic/versions/0001_initial_schema.py`, `0002_exports_row_count.py`, `0003_annotation_updated_at.py` |

There is **no message broker, no queue, no pub/sub**. Edge 4 (router → BackgroundTasks) is a direct in-process function call dispatched by FastAPI's thread pool after the HTTP response is sent.

---

## 3. Persistence at a glance

### PostgreSQL — 14 tables across 5 domains

| Domain | Tables |
|---|---|
| Identity | `users`, `audit_events` |
| Project setup | `projects`, `datasets`, `source_examples`, `task_templates` |
| Tasking | `tasks`, `assignments` |
| Quality | `annotations`, `model_suggestions`, `consensus_results`, `review_decisions`, `gold_labels` |
| Output | `exports` |

Full column-level catalog with foreign keys lives in [`process-flows.md`](./process-flows.md#postgresql-table-catalog) — that doc is where "what is saved where" gets the full treatment.

### Filesystem

- **Path:** `EXPORTS_DIR/{export_id}.{format}`, defaulting to `./exports/` relative to the uvicorn working directory (`backend/app/config.py:13`).
- **Filename pattern:** `{export_id}.jsonl` or `{export_id}.csv`, written at `backend/app/services/export.py:188`.
- **Lifetime:** Ephemeral. The current `docker-compose.yml` mounts no volume for `./exports/`, so files are lost when the backend container is recreated. Worth flagging in any deployment doc.
- **No upload storage.** Dataset uploads are parsed in memory in `backend/app/routers/datasets.py:25` and immediately turned into `SourceExample` rows; the original file never hits disk.

### Alembic

- **Location:** `backend/alembic/versions/`
- **Migrations on disk:** 3 — current head **`0003`**.
- **Run trigger:** `backend/entrypoint.sh` invokes `alembic upgrade head` once on container start, before `uvicorn` boots.

---

## 4. Deployment topology

### docker-compose service graph

```
frontend (3000)
   └─ depends_on: backend

backend (8000)
   ├─ env_file: .env
   ├─ env override: DATABASE_URL → postgres container
   └─ depends_on:
        postgres (condition: service_healthy)

postgres (5432)
   ├─ image: postgres:16-alpine
   ├─ healthcheck: pg_isready every 5s
   └─ volume: postgres_data
```

No separate worker container — background jobs run inside the `backend` container.

> **Honest footnote about `docker-compose.yml`.** The compose file as it sits today *also* starts a `redis:7-alpine` container on port 6379 and the backend has a `depends_on: redis` (`condition: service_started`) entry. **No application code uses Redis** — there is no `redis-py`/`aioredis` import anywhere in `backend/app/`. It is leftover infrastructure. You can safely delete the `redis` service block and the matching `depends_on` entry from `docker-compose.yml` without any behavioural change. This doc reflects what the system *actually does*, not what the compose file currently provisions.

### Environment variables actually consumed in code

| Variable | Read at | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | `backend/app/config.py:7` | `postgresql+psycopg://postgres:postgres@localhost:5432/collectlite` | SQLAlchemy engine URL |
| `REDIS_URL` | `backend/app/config.py:8` | `redis://localhost:6379/0` | Parsed by `Settings`; **no application code reads `settings.redis_url`** — listed here only because pydantic-settings loads it. Safe to drop from `.env`. |
| `COHERE_API_KEY` | `backend/app/config.py:9` | `""` | Empty → frontend falls back to Jaccard suggestion |
| `SECRET_KEY` | `backend/app/config.py:10` | `"change-me-in-production"` | Loaded into `Settings`; not actively used by current auth path |
| `DEBUG` | `backend/app/config.py:11` | `True` | Toggles SQLAlchemy `echo=` |
| `ALLOWED_ORIGINS` | `backend/app/config.py:12` | `"http://localhost:3000"` | Comma-separated CORS allow-list |
| `EXPORTS_DIR` | `backend/app/config.py:13` | `"exports"` | Filesystem directory for export files |
| `NEXT_PUBLIC_API_URL` | `frontend/src/lib/api.ts` | `"http://localhost:8000"` | Backend base URL used by all frontend API calls |

---

## 5. Architectural quirks worth showing on the diagram

These are the surprises that bite a reader who tries to map the diagram to "a normal microservice setup":

1. **BackgroundTasks are in-process.** `compute_consensus`, `generate_tasks`, and `create_export` (`backend/app/workers/jobs.py`) run in the same Python process as the API server. There is no Celery, no RQ, no broker. Draw them as a bubble *inside* the backend box, not as a separate service.
2. **Cohere is called synchronously inline.** `POST /api/tasks/{id}/suggestion` (`backend/app/routers/tasks.py:230`) blocks the request thread while the rerank call is in flight. It is **not** dispatched as a background job.
3. **Export files are ephemeral.** No volume mount for `./exports/` in `docker-compose.yml`; a container restart loses every export. Worth a callout box on the diagram next to the filesystem icon.
4. **No real auth.** `annotator_id` is selected from a frontend dropdown (`frontend/src/app/tasks/[taskId]/page.tsx`); the two demo users are lazily provisioned by `GET /api/annotators` (`backend/app/services/users.py`). A NextAuth route handler exists at `frontend/src/app/api/auth/[...nextauth]/route.ts` but is not wired into the API call path.

---

## 6. Excalidraw layout guide

A concrete suggestion — adjust as you like, but the structure below maps cleanly onto the edge list above.

### Suggested layered layout

```
┌────────────────────────────────────────────────────────────────┐
│                         BROWSER (user)                          │   ← top
└──────────────────┬─────────────────────────────────────────────┘
                   │ HTTP (3000)                       (edge #1)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│                  Next.js Frontend  (port 3000)                  │
│   App Router pages · TanStack Query · api.ts fetch wrapper      │
└──────────────────┬─────────────────────────────────────────────┘
                   │ HTTP/REST JSON (8000)             (edge #2)
                   ▼
┌────────────────────────────────────────────────────────────────┐
│                FastAPI Backend  (port 8000, one container)      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Routers (10): projects · datasets · tasks · annotations  │  │
│  │  · suggestions · consensus · reviews · metrics · exports  │  │
│  │  · users                                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  In-process BackgroundTasks                                │  │  ← nested bubble, same color family
│  │  generate_tasks · compute_consensus · create_export        │  │     as the backend, dashed border to
│  │                                                            │  │     signal "lives inside the process"
│  └──────────────────────────────────────────────────────────┘  │
└────┬─────────────────────────┬──────────────────────────┬──────┘
     │ SQL (psycopg3)          │ HTTPS (cohere SDK)       │ file write/read
     │ (edges #3, #5)          │ (edge #8)                │ (edges #6, #7)
     ▼                         ▼                          ▼
┌────────────┐         ┌──────────────┐          ┌────────────────┐
│ PostgreSQL │         │ Cohere       │          │ Filesystem     │
│ 16 (5432)  │         │ Rerank API   │          │ ./exports/     │
│ 14 tables  │         │ (external)   │          │ (ephemeral —   │
│            │         │              │          │  no volume)    │
└────────────┘         └──────────────┘          └────────────────┘
     ▲
     │ DDL on boot   (edge #9)
     │
┌────────────┐
│ Alembic    │  ← small box, clearly labelled "one-shot, runs once at backend start"
│ migrations │
└────────────┘
```

### Color suggestions

| Element | Suggested fill |
|---|---|
| Browser | Neutral grey |
| Frontend | Soft blue (`#dbeafe` / Tailwind blue-100) |
| Backend (outer) | Soft purple (`#ede9fe`) |
| BackgroundTasks bubble (nested) | Slightly darker purple, **dashed border** |
| PostgreSQL | Green (`#dcfce7`) |
| Cohere | Red/orange to flag external dependency (`#fee2e2`) |
| Filesystem | Yellow (`#fef9c3`) — pair with a small "ephemeral!" sticky note |
| Alembic | Same green as PostgreSQL but with a dashed outline (one-shot, not always running) |

### Edge labelling tips

- Label edges with **protocol + purpose**, not just protocol: `HTTP /api/* (REST JSON)` is more useful than just `HTTP`.
- Use a different arrow style (e.g. dotted) for edge #4 (router → BackgroundTasks) to signal "in-process function call, not a network hop".
- Put a short callout next to the Cohere arrow: **"synchronous, inline — blocks request thread"**.
- Put a callout next to `./exports/`: **"no volume mount → wiped on container restart"**.

---

## 7. Cross-references

- Per-flow detail (writes/reads/state transitions) → [`process-flows.md`](./process-flows.md)
- API surface → [`../api.md`](../api.md)
- Demo walkthrough → [`../demo-script.md`](../demo-script.md)
- Quick architecture overview → [`../architecture.md`](../architecture.md)
