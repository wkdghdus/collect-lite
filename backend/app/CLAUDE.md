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
| `routers/` | 9 APIRouter files — `projects`, `datasets` (upload + list), `tasks.generate_tasks` + `tasks.list_project_tasks`, and `annotations.submit_annotation` are implemented; the rest of `tasks.py`, `annotations.skip_task`, and the other routers remain stubbed with `raise NotImplementedError` |
| `services/` | Business logic called by routers (ingestion, task_generation, assignment, model_suggestions, cohere_service, consensus, review, export, audit) |
| `workers/` | `jobs.py` — FastAPI BackgroundTasks wrappers for async jobs |

## Task State Machine

```
created → suggested → assigned → submitted → needs_review → resolved → exported
created → assigned  (when skipping suggestion step)
submitted → needs_review → resolved  (disagreement path)
submitted → resolved                 (auto-resolve path; consensus has full agreement)
```

The `submitted → resolved` and `submitted → needs_review` transitions are driven by
`services/consensus.compute_consensus`, scheduled as a background task by
`routers/annotations.submit_annotation` once the human annotation pool is full
(`len(annotations) >= task.required_annotations`). Full human + model agreement
auto-resolves; any disagreement (or a model suggestion that does not match the
majority) routes the task to `needs_review`.

Return **409 Conflict** on invalid transitions. Never skip states.

## Idempotency Rules

- Dataset rows: deduplicated by `source_hash` (SHA-256 of JSON payload)
- Task generation: idempotent by `(project_id, example_id, template_id)`
- Exports: versioned by `schema_version` + `file_path`
