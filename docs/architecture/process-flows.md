# Process Flows — CollectLite

> Last verified against commit: **47cda7f**

This doc is the **dynamic** counterpart to [`system-design.md`](./system-design.md). It answers two questions:

1. For each end-to-end process, **which components are touched in what order?**
2. **What is written and read in each component during that process?**

It is the source for the *process-flows* Excalidraw diagram (one swimlane per component, one section per flow).

> Throughout this doc, "BackgroundTasks" means FastAPI's in-process `BackgroundTasks` mechanism (`backend/app/workers/jobs.py`). It runs in the same Python process as the API; there is no broker or queue behind it.

---

## How to read each flow

Each flow has the same shape:

- **Trigger** — what starts the flow (UI action, schedule, etc.).
- **Sequence** — numbered steps with a **lane prefix** (`frontend:` / `backend:` / `bgtask:` / `postgres:` / `filesystem:` / `cohere:`).
- **Writes** — every row inserted or updated, by table.
- **Reads** — tables queried.
- **State transitions** — relevant `Task.status` / `Assignment.status` / `Export.status` movement.
- **Entry-point ref** — the router file:line that owns the HTTP handler.

---

## Task state machine

The `tasks.status` column is the central invariant of the system. It is a `CHECK`-constrained string in `backend/app/models/task.py:27`. Seven states:

```
created → suggested → assigned → submitted → needs_review → resolved → exported
```

| Transition | Driver | Where |
|---|---|---|
| (insert) → `created` | Task generation job inserts new task rows | `backend/app/services/task_generation.py:10` |
| `created` → `suggested` | First model suggestion generated for the task | `backend/app/services/model_suggestions.py:59` |
| `created`/`suggested` → `assigned` | Annotator submits **first** annotation but `count < required_annotations` | `backend/app/routers/annotations.py:59` |
| `assigned` → `submitted` | Annotation count reaches `required_annotations` | `backend/app/routers/annotations.py:59` |
| `submitted` → `needs_review` | Consensus job finds disagreement (annotators vs each other, or vs latest model suggestion) | `backend/app/services/consensus.py:46` |
| `submitted` → `resolved` | Consensus job finds full agreement | `backend/app/services/consensus.py:46` |
| `needs_review` → `resolved` | Reviewer submits final label via `POST /api/tasks/{id}/review` | `backend/app/services/review.py:40` |
| `resolved` → `exported` | Task included in a successful export job | `backend/app/services/export.py:167` |

> **Lock rules.** `LOCKED_TASK_STATUSES = {needs_review, resolved, exported}` (defined in `backend/app/routers/annotations.py`). When a task is in any of these statuses, `PATCH /api/tasks/{task_id}/annotations/{annotation_id}` returns 409 — annotators cannot edit their submission once the task has progressed past their phase.

---

## PostgreSQL table catalog

All 14 tables. Columns shown are the load-bearing ones; full schema is in `backend/app/models/`.

### Identity

**`users`** — `backend/app/models/user.py:11`
- `id` UUID PK · `email` unique · `name` · `role` (CHECK: admin/owner/annotator/reviewer) · `created_at`
- has-many `annotations`, `review_decisions`

**`audit_events`** — `backend/app/models/audit.py:11`
- `id` UUID PK · `actor_id` FK→users (nullable) · `event_type` (e.g. `task.review_submitted`) · `entity_type` · `entity_id` UUID · `payload` JSONB · `created_at`
- Currently written only by `services/review.submit_review_decision`.

### Project setup

**`projects`** — `backend/app/models/project.py:11`
- `id` UUID PK · `name` · `description` · `owner_id` FK→users (nullable) · `task_type` · `status` (draft/active/paused/completed) · `created_at` · `updated_at`

**`datasets`** — `backend/app/models/dataset.py:19`
- `id` UUID PK · `project_id` FK→projects · `filename` · `schema_version` · `row_count` · `status` (uploaded/validated/failed) · `created_at`

**`source_examples`** — `backend/app/models/dataset.py:48`
- `id` UUID PK · `dataset_id` FK→datasets · `project_id` FK→projects · `external_id` · `source_hash` (SHA-256) · `payload` JSONB (`{query, candidate_document, document_id, metadata}`) · `created_at`
- UNIQUE `(project_id, source_hash)` — dedup key.

**`task_templates`** — `backend/app/models/task.py:12`
- `id` UUID PK · `project_id` FK→projects · `name` · `instructions` · `label_schema` JSONB · `version` · `created_at`

### Tasking

**`tasks`** — `backend/app/models/task.py:27`
- `id` UUID PK · `project_id` FK · `example_id` FK→source_examples · `template_id` FK→task_templates · `status` (7-state machine above) · `priority` · `required_annotations` · `created_at` · `updated_at`

**`assignments`** — `backend/app/models/task.py:84`
- `id` UUID PK · `task_id` FK · `annotator_id` FK→users · `status` (assigned/submitted/skipped/expired) · `started_at` · `submitted_at`
- One row per `(task_id, annotator_id)` pair, ensured by `services/assignment.ensure_assignment`.

### Quality

**`annotations`** — `backend/app/models/annotation.py:21`
- `id` UUID PK · `task_id` FK · `assignment_id` FK · `annotator_id` FK→users · `label` JSONB · `confidence` 1-5 · `notes` · `model_suggestion_visible` · `latency_ms` · `created_at` · `updated_at` (added in migration `0003`).

**`model_suggestions`** — `backend/app/models/annotation.py:57`
- `id` UUID PK · `task_id` FK · `provider` (`cohere`/`local`) · `model_name` · `suggestion` JSONB · `confidence` NUMERIC · `raw_response` JSONB · `latency_ms` · `cost_estimate_usd` · `created_at`

**`consensus_results`** — `backend/app/models/quality.py:11`
- `id` UUID PK · `task_id` FK · `final_label` JSONB · `agreement_score` NUMERIC · `method` (e.g. `majority_vote`) · `num_annotations` · `status` (auto_resolved/needs_review/review_resolved) · `created_at`

**`review_decisions`** — `backend/app/models/quality.py:37`
- `id` UUID PK · `task_id` FK · `reviewer_id` FK→users · `final_label` JSONB · `reason` · `created_at`

**`gold_labels`** — `backend/app/models/quality.py:57`
- `id` UUID PK · `task_id` FK · `expected_label` JSONB · `created_by` FK→users · `created_at`
- Schema-only today; no router writes to this table yet.

### Output

**`exports`** — `backend/app/models/export.py:11`
- `id` UUID PK · `project_id` FK · `format` (jsonl/csv) · `status` (queued/running/completed/failed) · `file_path` (nullable) · `row_count` · `schema_version` · `created_at`

---

## Flow 1 — Project & dataset upload

**Trigger:** Admin creates a project, then uploads a JSONL/CSV dataset.

### Sequence

1. **frontend:** `POST /api/projects` with `{name, task_type, description}` (`frontend/src/app/projects/new/page.tsx`).
2. **backend:** `routers/projects.py:15` inserts a `Project` row, then calls `services/task_templates.ensure_default_template` to seed a default `TaskTemplate` for `rag_relevance` projects.
3. **postgres:** `projects` row inserted; `task_templates` row inserted.
4. **frontend:** `POST /api/projects/{id}/datasets` (multipart) (`frontend/src/components/DatasetUploader.tsx`).
5. **backend:** `routers/datasets.py:25` reads the upload stream, calls `services/ingestion.parse_upload` (JSONL or CSV), then `normalize_rows` (pointwise/pairwise expansion), SHA-256 dedup against existing `source_examples`, and bulk-inserts.
6. **postgres:** `datasets` row inserted with `status='uploaded'`; `source_examples` rows inserted (only those whose `source_hash` is new for the project).

### Writes

- `projects` (insert)
- `task_templates` (insert — default seed)
- `datasets` (insert)
- `source_examples` (bulk insert, dedup by `source_hash`)

### Reads

- `source_examples` (existence check for dedup)
- `task_templates` (existence check before seeding default)

### State transitions

- `Dataset.status` set to `uploaded` (or `failed` on parse error).

### Entry-point ref

- Project: `backend/app/routers/projects.py:15`
- Dataset: `backend/app/routers/datasets.py:25`

---

## Flow 2 — Task generation (background)

**Trigger:** Admin clicks "Generate tasks" on the project task page.

### Sequence

1. **frontend:** `POST /api/projects/{id}/tasks/generate` with `{template_id, dataset_id?, required_annotations}` (`frontend/src/app/projects/[projectId]/tasks/page.tsx`).
2. **backend:** `routers/tasks.py:109` validates the project + template, calls `background_tasks.add_task(jobs.generate_tasks, ...)` and returns 202.
3. **bgtask:** `jobs.generate_tasks` (`backend/app/workers/jobs.py:9`) opens its own `SessionLocal()` and calls `services/task_generation.generate_tasks_for_project` (`backend/app/services/task_generation.py:10`).
4. **postgres:** Bulk inserts `Task` rows for every `SourceExample` in the project (or filtered by `dataset_id`) that does not yet have a Task for `(project_id, template_id)`. New tasks get `status='created'`.

### Writes

- `tasks` (bulk insert with `status='created'`)

### Reads

- `projects`, `task_templates` (validation)
- `source_examples` (driver list)
- `tasks` (existence check for idempotency)

### State transitions

- New `Task.status='created'`. (Frontend then polls and refreshes.)

### Entry-point ref

- `backend/app/routers/tasks.py:109`

---

## Flow 3 — Model suggestion generation (synchronous, inline)

**Trigger:** Annotator opens a task and clicks "Generate model suggestion", or the workbench auto-requests one on first load.

### Sequence

1. **frontend:** `POST /api/tasks/{taskId}/suggestion` (`frontend/src/app/tasks/[taskId]/page.tsx`).
2. **backend:** `routers/tasks.py:230` calls `services/model_suggestions.generate_suggestion_for_task` (`backend/app/services/model_suggestions.py:59`).
3. **postgres:** Reads `SourceExample.payload` for `query` + `candidate_document`.
4. Branch (a): `COHERE_API_KEY` is set → **cohere:** `services/cohere_service.generate_rerank_suggestion` (`backend/app/services/cohere_service.py:23`) — synchronous HTTPS call to `rerank-english-v3.0` returning `(score, label, raw_response)`.
   Branch (b): no key → `_local_suggestion` (Jaccard overlap) at `backend/app/services/model_suggestions.py:53`.
5. **postgres:** Insert `ModelSuggestion` row with provider/model/score/raw_response.
6. **postgres:** If `Task.status == 'created'`, update to `'suggested'`.

### Writes

- `model_suggestions` (insert)
- `tasks` (status update: `created` → `suggested`)

### Reads

- `tasks`, `source_examples` (payload)

### State transitions

- `Task.status: created → suggested` (only on first suggestion).

### Entry-point ref

- `backend/app/routers/tasks.py:230`

---

## Flow 4 — Annotation submit + consensus

**Trigger:** Annotator picks a label + confidence in the workbench and clicks Submit.

### Sequence

1. **frontend:** `POST /api/tasks/{taskId}/annotations` with `{annotator_id, label, confidence, model_suggestion_visible}` (`frontend/src/app/tasks/[taskId]/page.tsx`).
2. **backend:** `routers/annotations.py:59` (`submit_annotation`):
   - Looks up or lazily creates an `Assignment` via `services/assignment.ensure_assignment`.
   - Inserts an `Annotation` row.
   - Sets `Assignment.status='submitted'`.
   - Counts annotations for the task; if `count >= required_annotations`, sets `Task.status='submitted'`, else `Task.status='assigned'`.
   - Calls `background_tasks.add_task(jobs.compute_consensus, task_id)`.
3. **bgtask:** `jobs.compute_consensus` → `services/consensus.compute_consensus` (`backend/app/services/consensus.py:46`):
   - Reads all `annotations` for the task and the latest `model_suggestion`.
   - Runs majority vote.
   - Inserts/updates a `consensus_results` row.
   - If full human agreement AND model agrees → `consensus_results.status='auto_resolved'`, `Task.status='resolved'`.
   - Else → `consensus_results.status='needs_review'`, `Task.status='needs_review'`.
4. **frontend:** After submit, fetches `GET /api/tasks/next?project_id=...&annotator_id=...&exclude_task_id=...` and navigates to the next task.

### Writes

- `assignments` (insert on first submit, update `status='submitted'` thereafter)
- `annotations` (insert)
- `tasks` (status update: → `assigned` or `submitted`)
- `consensus_results` (insert by background task)
- `tasks` second update (background task: → `resolved` or `needs_review`)

### Reads

- `tasks`, `users`, `assignments`, `annotations`, `model_suggestions`

### State transitions

- `Assignment.status: assigned → submitted`
- `Task.status: created/suggested → assigned → submitted → {resolved | needs_review}`

### Entry-point ref

- Submit: `backend/app/routers/annotations.py:59`
- Next-task fetch: `backend/app/routers/tasks.py:158`

---

## Flow 5 — Annotation edit (with lock rules)

**Trigger:** Annotator returns to a task they've already labeled and edits their annotation.

### Sequence

1. **frontend:** Workbench detects `myAnnotation != null` and `task.status NOT IN LOCKED_TASK_STATUSES`, sets `mode='edit'`, shows the "editing your submission" banner.
2. **frontend:** `PATCH /api/tasks/{taskId}/annotations/{annotationId}` with the same body shape as submit (partial update allowed).
3. **backend:** `routers/annotations.py:137` (`update_annotation`):
   - Returns 404 if annotation is missing.
   - Returns 403 if `annotation.annotator_id != body.annotator_id` or `annotation.task_id != path task_id`.
   - Returns 409 if `task.status ∈ LOCKED_TASK_STATUSES = {needs_review, resolved, exported}`.
   - Applies non-None fields, bumps `annotation.updated_at` (driven by `onupdate=func.now()` on the column, see migration `0003`).
   - If `task.status == 'submitted'`, schedules `jobs.compute_consensus` so the consensus reflects the edited label.

### Writes

- `annotations` (update; `updated_at` auto-bumps)
- `consensus_results` (re-computed by background task, only when `task.status == 'submitted'` at edit time)

### Reads

- `annotations`, `tasks`

### State transitions

- None directly. The re-scheduled consensus task may move `Task.status: submitted → resolved/needs_review`.

### Entry-point ref

- `backend/app/routers/annotations.py:137`

---

## Flow 6 — Review queue resolution

**Trigger:** Reviewer opens the project review page and submits a final label for a `needs_review` task.

### Sequence

1. **frontend:** `GET /api/projects/{projectId}/review/tasks` (`frontend/src/app/projects/[projectId]/review/page.tsx`).
2. **backend:** `routers/reviews.py:103` → `services/review.list_review_queue` returns all tasks with `status='needs_review'`, eager-loaded with example/annotations/suggestions/consensus.
3. **frontend:** Reviewer submits `POST /api/tasks/{taskId}/review` with `{final_label, reason, reviewer_id?}`.
4. **backend:** `routers/reviews.py:116` → `services/review.submit_review_decision` (`backend/app/services/review.py:40`):
   - Validates `task.status == 'needs_review'` (409 otherwise).
   - If `reviewer_id` is null, lazily creates the singleton `system-reviewer@collectlite.local` user.
   - Inserts `review_decisions` row.
   - Updates the latest `consensus_results.final_label` and sets `consensus_results.status='review_resolved'`.
   - Sets `Task.status='resolved'`.
   - Inserts an `audit_events` row with `event_type='task.review_submitted'` (`backend/app/services/audit.py:7`).

### Writes

- `users` (insert — only on first review when `reviewer_id` is null)
- `review_decisions` (insert)
- `consensus_results` (update: `final_label`, `status='review_resolved'`)
- `tasks` (status update: `needs_review → resolved`)
- `audit_events` (insert)

### Reads

- `tasks`, `consensus_results`, `users`

### State transitions

- `Task.status: needs_review → resolved`
- `ConsensusResult.status: needs_review → review_resolved`

### Entry-point ref

- List: `backend/app/routers/reviews.py:103`
- Submit: `backend/app/routers/reviews.py:116`

---

## Flow 7 — Export (background, file write)

**Trigger:** User clicks "Create export" with format JSONL or CSV.

### Sequence

1. **frontend:** `POST /api/projects/{projectId}/exports` with `{format}` (`frontend/src/app/projects/[projectId]/exports/page.tsx`).
2. **backend:** `routers/exports.py:27` inserts an `Export` row with `status='queued'`, calls `background_tasks.add_task(jobs.create_export, export_id)`, returns 202.
3. **bgtask:** `jobs.create_export` → `services/export.run_export_job` (`backend/app/services/export.py:167`):
   - Sets `Export.status='running'`.
   - Reads all `Task(status='resolved')` for the project, eager-loaded with example/consensus/suggestions.
   - For each task: assembles a row from `SourceExample.payload` + latest `ConsensusResult` + latest `ModelSuggestion` + `ReviewDecision` existence (informs `label_source` field).
   - Serializes to JSONL or CSV.
4. **filesystem:** Writes `EXPORTS_DIR/{export_id}.{format}` (`backend/app/services/export.py:188`).
5. **postgres:** Sets each included task `status='exported'`. Sets `Export.status='completed'`, populates `file_path` and `row_count`. (On failure: rollback, delete partial file, `Export.status='failed'`.)
6. **frontend:** Polls `GET /api/projects/{projectId}/exports` every 2 s while any export is non-terminal.
7. **frontend → backend → filesystem:** When ready, user clicks the download link → `GET /api/exports/{id}/download` (`backend/app/routers/exports.py:77`) returns a `FileResponse` streaming the file.

### Writes

- `exports` (insert with `status='queued'`, then update `running` → `completed`/`failed`, plus `file_path`, `row_count`)
- `tasks` (bulk status update: `resolved → exported` for included tasks)
- **filesystem:** `EXPORTS_DIR/{export_id}.{format}` (created on success, deleted on failure)

### Reads

- `exports`, `tasks`, `consensus_results`, `model_suggestions`, `review_decisions`, `source_examples`

### State transitions

- `Export.status: queued → running → completed | failed`
- `Task.status: resolved → exported` (only for tasks included in the successful export)

### Entry-point ref

- Create: `backend/app/routers/exports.py:27`
- Download: `backend/app/routers/exports.py:77`

---

## Flow 8 — Metrics dashboard read

**Trigger:** User opens the project metrics page.

### Sequence

1. **frontend:** `GET /api/projects/{projectId}/metrics` (`frontend/src/app/projects/[projectId]/metrics/page.tsx`).
2. **backend:** `routers/metrics.py:15` → `services/metrics.compute_project_metrics`:
   - Groups task counts by all 7 statuses.
   - Finds the latest `consensus_results` per task via subquery → computes `avg_human_agreement`.
   - Finds the latest `model_suggestions` per task → computes `model_human_agreement_rate` (model label vs consensus final label).
   - Builds a `final_label_distribution` `Counter`.
3. **frontend:** Renders workflow funnel, quality cards, and the label distribution list.

### Writes

- None. Pure read.

### Reads

- `tasks`, `consensus_results`, `model_suggestions`

### State transitions

- None.

### Entry-point ref

- `backend/app/routers/metrics.py:15`

---

## Cross-flow write matrix

Rows are flows; columns are tables. `X` means the flow inserts or updates rows in that table. Useful for spotting read-after-write hazards (e.g. flow 5 may invalidate consensus written by flow 4).

| Flow | users | audit_events | projects | datasets | source_examples | task_templates | tasks | assignments | annotations | model_suggestions | consensus_results | review_decisions | exports |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 Project & dataset upload | | | X | X | X | X | | | | | | | |
| 2 Task generation | | | | | | | X | | | | | | |
| 3 Model suggestion | | | | | | | X | | | X | | | |
| 4 Annotation submit + consensus | | | | | | | X | X | X | | X | | |
| 5 Annotation edit | | | | | | | | | X | | X (re-comp) | | |
| 6 Review resolution | X (lazy) | X | | | | | X | | | | X | X | |
| 7 Export | | | | | | | X | | | | | | X |
| 8 Metrics read | | | | | | | | | | | | | |

`gold_labels` is omitted because no flow currently writes to it.

---

## Excalidraw layout guide

### Suggested swimlane structure

Stack lanes top-to-bottom in this order — it matches the lane prefixes used in every flow above:

```
┌──────────────────────────────────────────────────────────────────┐
│ Browser                                                           │
├──────────────────────────────────────────────────────────────────┤
│ Frontend  (Next.js)                                               │
├──────────────────────────────────────────────────────────────────┤
│ API  (FastAPI routers)                                            │
├──────────────────────────────────────────────────────────────────┤
│ BackgroundTasks  (in-process — same color as API, dashed border)  │
├──────────────────────────────────────────────────────────────────┤
│ PostgreSQL                                                        │
├──────────────────────────────────────────────────────────────────┤
│ Filesystem  (only used by Flow 7)                                 │
├──────────────────────────────────────────────────────────────────┤
│ Cohere  (only used by Flow 3, branch a)                           │
└──────────────────────────────────────────────────────────────────┘
```

For each flow, draw arrows hopping between lanes left-to-right in step order. Suggested conventions:

| Convention | Meaning |
|---|---|
| **Solid arrow, blue** | HTTP request |
| **Dotted arrow, purple** | In-process function call (router → BackgroundTasks) |
| **Solid arrow, green** | DB write (`INSERT` / `UPDATE`) |
| **Solid arrow, grey** | DB read (`SELECT`) |
| **Solid arrow, yellow** | Filesystem write/read |
| **Solid arrow, red** | External HTTPS (Cohere) |
| **Sticky note** | State transition (e.g. `Task.status: submitted → needs_review`) |

### Sub-diagram: task state machine

Place this somewhere next to the swimlanes:

```
created ──► suggested ──► assigned ──► submitted ──► needs_review ──► resolved ──► exported
                                                  └──────► resolved ─────────────┘
```

Annotate each arrow with the file:line that triggers it (see the **Task state machine** section above).

### Tips

- **One Excalidraw frame per flow.** Each frame uses the same lane layout so flows can be compared side-by-side.
- Highlight the **only flows that touch the filesystem** (Flow 7) and **the only flow that reaches Cohere** (Flow 3) — those lanes will be empty in every other frame.
- Flow 4 → Flow 5 → Flow 4-revisited is the most subtle interaction in the system: an edit re-runs consensus only if `task.status == 'submitted'` at edit time. Worth a small inset diagram showing that re-entry path.

---

## Cross-references

- Static topology + components → [`system-design.md`](./system-design.md)
- API surface → [`../api.md`](../api.md)
- Demo walkthrough → [`../demo-script.md`](../demo-script.md)
