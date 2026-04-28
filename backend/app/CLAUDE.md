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
| `routers/` | 10 APIRouter files — `projects` (POST auto-seeds a default `TaskTemplate` for known `task_type`s via `services/task_templates.ensure_default_template`), `datasets` (upload + list), `tasks.generate_tasks` (POST body now requires `dataset_id`; tasks are scoped to the chosen dataset's source rows) + `tasks.list_project_tasks` + `tasks.list_project_templates` (GET `/projects/{project_id}/templates`, newest-first) + `tasks.get_task` (GET `/tasks/{task_id}` returns a `TaskDetailResponse` with embedded source-payload fields, latest model suggestion, and annotation summaries) + `tasks.get_next_task` (GET `/tasks/next` — picks the highest-priority `created`/`suggested`/`assigned` task, oldest first; optional `project_id`, `annotator_id` (excludes tasks already annotated by that annotator), and `exclude_task_id` query params; returns `null` when no eligible task exists) + `tasks.create_task_suggestion` (POST `/tasks/{task_id}/suggestion`), `suggestions.list_suggestions` (GET `/tasks/{task_id}/suggestions`, newest-first), `annotations.submit_annotation` (accepts EITHER `assignment_id` OR `annotator_id` in the request body; when only `annotator_id` is supplied the router calls `services/assignment.ensure_assignment` to lazily create or reuse an Assignment for the (task, annotator) pair — one Assignment per pair, so a duplicate submission still returns 409), `reviews.list_review_tasks` (GET `/projects/{project_id}/review/tasks`) + `reviews.submit_review` (POST `/tasks/{task_id}/review`), `exports.create_export` (POST `/projects/{project_id}/exports`) + `exports.list_exports` (GET `/projects/{project_id}/exports`) + `exports.get_export` (GET `/exports/{export_id}`) + `exports.download_export` (GET `/exports/{export_id}/download`), `metrics.get_project_metrics` (GET `/projects/{project_id}/metrics` — dashboard snapshot returning `total_tasks`, per-status counts for the seven canonical statuses, `exportable_task_count` (= `resolved` count), `avg_human_agreement` (mean of latest `ConsensusResult.agreement_score` per task), `model_human_agreement_rate` (latest `ModelSuggestion` label vs latest `ConsensusResult.final_label` match rate; denominator excludes tasks without a suggestion), and `final_label_distribution` (Counter over the `relevance` value of the latest `ConsensusResult`); rate fields return `null` and distribution returns `{}` when there is no data), and `users.list_annotators` (GET `/annotators` — idempotent list of the two demo annotators `alice@collectlite.local` + `bob@collectlite.local`, lazily provisioned via `services/users.ensure_demo_annotators`) are implemented; the batch `POST /projects/{project_id}/tasks/suggest`, the plural batch `POST /tasks/{task_id}/suggestions`, `annotations.skip_task` and the other routers remain stubbed with `raise NotImplementedError` |
| `services/` | Business logic called by routers (ingestion, task_generation, task_templates (`ensure_default_template`), assignment, model_suggestions, cohere_service, consensus, review, export, audit) |
| `workers/` | `jobs.py` — FastAPI BackgroundTasks wrappers for async jobs |

## Task State Machine

```
created → suggested → assigned → submitted → needs_review → resolved → exported
created → assigned  (when skipping suggestion step)
submitted → needs_review → resolved  (disagreement path)
submitted → resolved                 (auto-resolve path; consensus has full agreement)
```

The `created → suggested` transition is driven by `services/model_suggestions.generate_suggestion_for_task`
via `POST /tasks/{task_id}/suggestion` (Cohere Rerank when `COHERE_API_KEY` is set, Jaccard
lexical-overlap fallback otherwise).

The `submitted → resolved` and `submitted → needs_review` transitions are driven by
`services/consensus.compute_consensus`, scheduled as a background task by
`routers/annotations.submit_annotation` once the human annotation pool is full
(`len(annotations) >= task.required_annotations`). Full human + model agreement
auto-resolves; any disagreement (or a model suggestion that does not match the
majority) routes the task to `needs_review`.

The `needs_review → resolved` transition is driven by
`services/review.submit_review_decision` via `POST /tasks/{task_id}/review`. The
service inserts a `ReviewDecision` row, updates the latest `ConsensusResult`
(`final_label` set to the reviewer's choice, `status='review_resolved'`), sets
`task.status='resolved'`, and emits a `task.review_submitted` audit event via
`services/audit.log_event`. The request body's `reviewer_id` is optional — when
omitted, the service lazily reuses (or creates) a singleton system reviewer
(`email='system-reviewer@collectlite.local'`, `role='reviewer'`).

Return **409 Conflict** on invalid transitions. Never skip states.

The `resolved → exported` transition is driven by `services/export.run_export_job`,
scheduled as a background task by `routers/exports.create_export` (POST
`/projects/{project_id}/exports`). The job assembles one row per resolved task
from `SourceExample.payload` + latest `ConsensusResult` + latest `ModelSuggestion`
(plus `ReviewDecision` existence for `label_source`), serialises to JSONL or CSV
under `settings.exports_dir`, persists `Export.file_path` + `Export.row_count` +
`Export.status='completed'`, and only then flips each included `Task.status` to
`exported`. Failure rolls back: `Export.status='failed'`, partial file deleted,
task statuses untouched.

## Idempotency Rules

- Dataset rows: deduplicated by `source_hash` (SHA-256 of JSON payload)
- Task generation: idempotent by `(project_id, example_id, template_id)`
- Exports: versioned by `schema_version` + `file_path`; re-running `POST /projects/{id}/exports` skips tasks already at `status='exported'`, so repeated calls are safe (the second export's `row_count` is 0)
