# backend/app/

FastAPI application package.

## Entry Points

- `main.py` — app factory: CORS middleware, latency header middleware, `/health`, all routers under `/api`
- `config.py` — `Settings` via pydantic-settings (reads `.env`)
- `db.py` — SQLAlchemy engine, `SessionLocal`, `Base`, `get_db` dependency

## Sub-packages

| Package | Contents |
|---------|---------|
| `models/` | 14 SQLAlchemy ORM models (one file per domain: user, project, dataset, task, annotation, quality, export, audit) |
| `schemas/` | Pydantic v2 request/response models matching each router |
| `routers/` | 9 APIRouter files — `projects` and `datasets` (upload + list) are implemented; the rest stubbed with `raise NotImplementedError` |
| `services/` | Business logic called by routers (ingestion, task_generation, assignment, model_suggestions, consensus, review, export, audit) |
| `workers/` | `jobs.py` — FastAPI BackgroundTasks wrappers for async jobs |

## Task State Machine

```
created → suggested → assigned → submitted → needs_review → resolved → exported
created → assigned  (when skipping suggestion step)
submitted → needs_review → resolved  (disagreement path)
```

Return **409 Conflict** on invalid transitions. Never skip states.

## Idempotency Rules

- Dataset rows: deduplicated by `source_hash` (SHA-256 of JSON payload)
- Task generation: idempotent by `(project_id, example_id, template_id)`
- Exports: versioned by `schema_version` + `file_path`
