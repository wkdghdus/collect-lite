# CollectLite Whole System Design

## 1. Product goal

CollectLite is a lower-scale internal human-data platform for creating high-quality labeled datasets for LLM/RAG training and evaluation. It combines:

- annotation project management
- dataset ingestion
- model-in-the-loop pre-labeling
- annotator work queues
- consensus and review workflows
- quality dashboards
- dataset export

The system is designed to be credible for a Cohere Collect SWE interview because it uses a Collect-relevant domain and a Cohere-aligned stack: Next.js, TypeScript, React, Python, and full-stack internal tooling patterns.

## 2. Users and permissions

### Roles

| Role | Capabilities |
|---|---|
| Admin | Create projects, manage users, configure task templates, export data. |
| Project Owner | Upload datasets, generate tasks, monitor quality, resolve reviews, export datasets. |
| Annotator | Complete assigned tasks, submit labels, add notes, skip unclear tasks. |
| Reviewer | Inspect disagreements, override labels, approve export readiness. |

### MVP permission model

Use simple role-based access control stored in the `users.role` column. Authentication can be implemented with NextAuth, Clerk, or a simple local JWT for speed.

## 3. Architecture overview

```text
                         ┌────────────────────────────┐
                         │        Next.js App          │
                         │  Admin / Annotator / Review │
                         └─────────────┬──────────────┘
                                       │ REST / JSON
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
│                                                                  │
│  Project API  Dataset API  Task API  Annotation API  Export API  │
│                                                                  │
│  Assignment Engine  Consensus Engine  Model Suggestion Service   │
└──────────────┬───────────────────────┬───────────────────────────┘
               │                       │
               ▼                       ▼
       ┌──────────────┐        ┌────────────────┐
       │ PostgreSQL   │        │ Redis / Queue  │
       │ relational   │        │ async jobs     │
       │ source truth │        │ suggestions    │
       └──────────────┘        │ exports        │
                               └────────────────┘
                                       │
                                       ▼
                         ┌────────────────────────────┐
                         │ Model Providers             │
                         │ Cohere Rerank / Embed       │
                         │ Local fallback models       │
                         └────────────────────────────┘
```

## 4. Core services

### Frontend: Next.js + TypeScript

Pages:

```text
/app
  /projects
  /projects/[projectId]
  /projects/[projectId]/datasets
  /projects/[projectId]/tasks
  /projects/[projectId]/review
  /projects/[projectId]/metrics
  /annotate
  /exports
```

Key components:

- `ProjectCard`
- `DatasetUploader`
- `TaskTemplateEditor`
- `AnnotationWorkbench`
- `ModelSuggestionPanel`
- `ReviewQueueTable`
- `ConsensusBadge`
- `MetricsDashboard`
- `ExportBuilder`

Frontend libraries:

- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Recharts
- Zod for client-side validation

### Backend: FastAPI + Python

Modules:

```text
backend/app
  main.py
  config.py
  db.py
  models/
  schemas/
  routers/
    projects.py
    datasets.py
    tasks.py
    annotations.py
    reviews.py
    metrics.py
    exports.py
  services/
    ingestion.py
    task_generation.py
    assignment.py
    model_suggestions.py
    consensus.py
    review.py
    export.py
    audit.py
  workers/
    jobs.py
```

Backend libraries:

- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- psycopg
- pandas
- cohere Python SDK
- sentence-transformers fallback
- pytest

## 5. Database schema

### users

```sql
id uuid primary key
email text unique not null
name text not null
role text not null check role in ('admin', 'owner', 'annotator', 'reviewer')
created_at timestamptz not null
```

### projects

```sql
id uuid primary key
name text not null
description text
owner_id uuid references users(id)
task_type text not null
status text not null check status in ('draft', 'active', 'paused', 'completed')
created_at timestamptz not null
updated_at timestamptz not null
```

### datasets

```sql
id uuid primary key
project_id uuid references projects(id)
filename text not null
schema_version text not null
row_count int not null
status text not null check status in ('uploaded', 'validated', 'failed')
created_at timestamptz not null
```

### source_examples

```sql
id uuid primary key
dataset_id uuid references datasets(id)
project_id uuid references projects(id)
external_id text
source_hash text not null
payload jsonb not null
created_at timestamptz not null
unique(project_id, source_hash)
```

### task_templates

```sql
id uuid primary key
project_id uuid references projects(id)
name text not null
instructions text not null
label_schema jsonb not null
version int not null
created_at timestamptz not null
```

### tasks

```sql
id uuid primary key
project_id uuid references projects(id)
example_id uuid references source_examples(id)
template_id uuid references task_templates(id)
status text not null check status in ('created', 'suggested', 'assigned', 'submitted', 'needs_review', 'resolved', 'exported')
priority int not null default 0
required_annotations int not null default 2
created_at timestamptz not null
updated_at timestamptz not null
```

### assignments

```sql
id uuid primary key
task_id uuid references tasks(id)
annotator_id uuid references users(id)
status text not null check status in ('assigned', 'submitted', 'skipped', 'expired')
started_at timestamptz
submitted_at timestamptz
```

### annotations

```sql
id uuid primary key
task_id uuid references tasks(id)
assignment_id uuid references assignments(id)
annotator_id uuid references users(id)
label jsonb not null
confidence int check confidence between 1 and 5
notes text
model_suggestion_visible boolean not null default true
latency_ms int
created_at timestamptz not null
```

### model_suggestions

```sql
id uuid primary key
task_id uuid references tasks(id)
provider text not null
model_name text not null
suggestion jsonb not null
confidence numeric
raw_response jsonb
latency_ms int
cost_estimate_usd numeric
created_at timestamptz not null
```

### consensus_results

```sql
id uuid primary key
task_id uuid references tasks(id)
final_label jsonb not null
agreement_score numeric not null
method text not null
num_annotations int not null
status text not null check status in ('auto_resolved', 'needs_review', 'review_resolved')
created_at timestamptz not null
```

### review_decisions

```sql
id uuid primary key
task_id uuid references tasks(id)
reviewer_id uuid references users(id)
final_label jsonb not null
reason text
created_at timestamptz not null
```

### gold_labels

```sql
id uuid primary key
task_id uuid references tasks(id)
expected_label jsonb not null
created_by uuid references users(id)
created_at timestamptz not null
```

### exports

```sql
id uuid primary key
project_id uuid references projects(id)
format text not null check format in ('jsonl', 'csv')
status text not null check status in ('queued', 'running', 'completed', 'failed')
file_path text
schema_version text not null
created_at timestamptz not null
```

### audit_events

```sql
id uuid primary key
actor_id uuid references users(id)
event_type text not null
entity_type text not null
entity_id uuid not null
payload jsonb
created_at timestamptz not null
```

## 6. Main workflows

### Workflow A: Dataset upload to task creation

```text
Project owner uploads CSV/JSONL
        ↓
Backend validates file schema
        ↓
Rows normalized into source_examples
        ↓
Project owner defines task template + instructions
        ↓
Task generator creates tasks from source_examples
        ↓
Tasks enter created state
```

Validation rules:

- Required columns depend on task type.
- Duplicate rows are detected using `source_hash`.
- Invalid rows are returned as validation errors.
- Raw payload is preserved in `source_examples.payload`.

### Workflow B: Model-in-the-loop suggestions

```text
Task enters created state
        ↓
Suggestion worker loads source payload
        ↓
Cohere Rerank / Embed / LLM suggestion runs
        ↓
model_suggestions row is written
        ↓
Task status becomes suggested
```

For MVP relevance labeling:

- Input: query and candidate documents.
- Model step: Cohere Rerank scores candidates.
- Output: ranked candidates, scores, top recommendation, rationale if available.

### Workflow C: Annotation

```text
Annotator requests next task
        ↓
Assignment engine locks available task
        ↓
Frontend displays task + instructions + optional model suggestion
        ↓
Annotator submits label, confidence, notes
        ↓
Assignment marked submitted
        ↓
Consensus engine checks whether enough annotations exist
```

Assignment policy:

- Avoid assigning the same task twice to the same annotator.
- Prefer high-priority tasks.
- Prefer tasks with fewer current annotations.
- Skip tasks already resolved or exported.

### Workflow D: Consensus and review

```text
Enough annotations exist
        ↓
Consensus engine computes agreement
        ↓
High agreement → task resolved
Low agreement → task needs_review
        ↓
Reviewer inspects all labels/model suggestions
        ↓
Reviewer submits final decision
        ↓
Task resolved
```

MVP consensus methods:

- Classification: majority vote.
- Relevance rating: average score + threshold.
- Pairwise preference: majority preference.
- Freeform critique: reviewer-only resolution.

### Workflow E: Export

```text
Project owner requests export
        ↓
Export worker gathers resolved tasks
        ↓
Training/eval split assigned
        ↓
JSONL or CSV generated
        ↓
Export record stores path and schema version
        ↓
Project owner downloads file
```

Example JSONL export:

```json
{
  "example_id": "...",
  "query": "What documents are needed for mortgage renewal?",
  "documents": ["...", "..."],
  "final_label": {"best_document_index": 0, "relevance": "high"},
  "agreement_score": 0.86,
  "num_annotations": 3,
  "model_suggestion": {"provider": "cohere", "model": "rerank", "scores": [0.91, 0.22]},
  "split": "train",
  "instruction_version": 2
}
```

## 7. API contract

### Project APIs

```http
POST /api/projects
GET /api/projects
GET /api/projects/{project_id}
PATCH /api/projects/{project_id}
```

### Dataset APIs

```http
POST /api/projects/{project_id}/datasets
GET /api/projects/{project_id}/datasets
GET /api/datasets/{dataset_id}/errors
```

### Task APIs

```http
POST /api/projects/{project_id}/tasks/generate
POST /api/projects/{project_id}/tasks/suggest
GET /api/tasks/next
GET /api/tasks/{task_id}
```

### Annotation APIs

```http
POST /api/tasks/{task_id}/annotations
POST /api/tasks/{task_id}/skip
```

### Review APIs

```http
GET /api/projects/{project_id}/review-queue
POST /api/reviews/{task_id}/resolve
```

### Metrics APIs

```http
GET /api/projects/{project_id}/metrics
```

Response includes:

```json
{
  "tasks_total": 1200,
  "tasks_resolved": 840,
  "review_backlog": 51,
  "agreement_rate": 0.78,
  "gold_accuracy": 0.91,
  "model_human_disagreement_rate": 0.24,
  "avg_annotation_latency_ms": 18400
}
```

### Export APIs

```http
POST /api/projects/{project_id}/exports
GET /api/exports/{export_id}
GET /api/exports/{export_id}/download
```

## 8. Frontend screens

### `/projects`

- List projects.
- Create project modal.
- Show status, task count, review backlog, export readiness.

### `/projects/[id]/datasets`

- Upload CSV/JSONL.
- Preview parsed rows.
- Show validation errors.
- Confirm ingestion.

### `/projects/[id]/tasks`

- Task counts by state.
- Generate tasks.
- Trigger model suggestions.
- Inspect task samples.

### `/annotate`

- Fetch next assigned task.
- Show instructions.
- Show query/context/candidates.
- Show model suggestion panel.
- Submit label/confidence/notes.
- Keyboard shortcuts for fast labeling.

### `/projects/[id]/review`

- Table of disagreement tasks.
- Side-by-side annotations.
- Model suggestion comparison.
- Reviewer final decision form.

### `/projects/[id]/metrics`

- Throughput chart.
- Agreement chart.
- Label distribution.
- Review backlog.
- Model-human disagreement.
- Annotator reliability leaderboard.

### `/exports`

- Create export.
- Download export.
- Inspect schema/version.

## 9. Background jobs

### Jobs

| Job | Purpose |
|---|---|
| `generate_tasks` | Convert source examples into tasks. |
| `run_model_suggestions` | Generate model-in-loop suggestions. |
| `compute_consensus` | Resolve or mark tasks for review. |
| `create_export` | Write JSONL/CSV export. |
| `refresh_metrics` | Materialize dashboard aggregates if needed. |

MVP can use FastAPI background tasks. A stronger implementation can use Redis Queue or Celery.

## 10. Observability

### Application logs

Log events:

- dataset uploaded
- validation failed
- tasks generated
- model suggestion failed/succeeded
- annotation submitted
- consensus computed
- review resolved
- export completed

### Metrics

- API latency
- model suggestion latency
- model suggestion error rate
- tasks completed per day
- review backlog size
- agreement rate
- export generation time

### Audit trail

Every user action that mutates important state writes to `audit_events`.

## 11. Reliability and correctness

### State transitions

Only allow valid transitions:

```text
created -> suggested -> assigned -> submitted -> resolved -> exported
created -> assigned
submitted -> needs_review -> resolved
```

Invalid transitions return 409 Conflict.

### Idempotency

- Dataset rows deduplicated by source hash.
- Task generation is idempotent by `(project_id, example_id, template_id)`.
- Exports have versioned schema and file path.

### Failure handling

- Model suggestion failures mark task as `created` with error metadata; annotation can still proceed.
- Export failures store an error and can be retried.
- Skipped tasks return to the pool unless skipped too many times.

## 12. Security and privacy

MVP:

- Authentication required for all app routes.
- Role checks for admin/review/export actions.
- Do not expose raw provider API keys to frontend.
- Store API keys only in backend environment variables.

Production improvements:

- Organization-level tenancy.
- Per-project access control.
- PII redaction before annotation.
- Encrypted object storage for exports.
- Signed export URLs.

## 13. Testing strategy

### Backend tests

- Dataset validation tests.
- Task generation idempotency tests.
- Assignment locking tests.
- Consensus tests.
- Export schema tests.

### Frontend tests

- Dataset upload flow.
- Annotation submission flow.
- Review resolution flow.
- Dashboard rendering.

### End-to-end test

Seed demo project, upload dataset, generate tasks, annotate tasks, resolve consensus, export JSONL.

## 14. Repo structure

```text
collect-lite/
  README.md
  docker-compose.yml
  .env.example
  project-description.md
  system-design.md
  frontend/
    app/
    components/
    lib/
    package.json
  backend/
    app/
    alembic/
    tests/
    pyproject.toml
  data/
    sample_relevance_tasks.jsonl
    sample_pairwise_preferences.jsonl
  docs/
    architecture.md
    api.md
    demo-script.md
```

## 15. Demo script for interview

1. Open the project dashboard.
2. Create a project named "RAG Relevance Evaluation".
3. Upload a JSONL file with queries and candidate documents.
4. Generate annotation tasks.
5. Run model suggestions using Cohere Rerank.
6. Switch to annotator view and complete several tasks.
7. Show model suggestion vs human label.
8. Create disagreement by submitting different labels as another annotator.
9. Resolve the disagreement in reviewer view.
10. Open metrics dashboard.
11. Export final JSONL dataset.
12. Explain how this maps to Collect's likely mission: human data collection, model evaluation, internal tooling, and model-in-the-loop annotation.

## 16. Build order

### Must-have

- Project CRUD
- Dataset upload
- Task generation
- Annotator UI
- Annotation submission
- Basic consensus
- JSONL export

### Should-have

- Cohere Rerank model suggestions
- Review queue
- Metrics dashboard
- Gold tasks
- Docker Compose

### Nice-to-have

- Keyboard shortcuts
- Active-learning priority
- Pairwise ranking aggregation
- OpenTelemetry
- RBAC polish
- Export version diffing

## 17. Interview positioning

Say:

"Based on public evidence, Collect appears to build internal human-data collection and curation workflows. I built a lower-scale version focused on the same system class: annotation task generation, model-in-the-loop suggestions, consensus, review, dashboards, and export contracts. I used a stack aligned with the Collect posting: Next.js, TypeScript, React, and Python/FastAPI."

Do not say:

"I rebuilt Cohere's internal Collect system."

Better wording:

"I designed and implemented a public-evidence-based reconstruction of the type of platform Collect likely owns."
