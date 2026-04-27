# backend/tests/

pytest suite for the FastAPI backend. Run from `backend/`.

## Commands

- **All tests:** `pytest tests/ -v`
- **Single file:** `pytest tests/test_consensus.py -v`
- **Single test:** `pytest tests/test_consensus.py::test_majority_vote_single_label -v`

## Fixtures (`conftest.py`)

- `client` — `TestClient(app, raise_server_exceptions=False)`
  - `raise_server_exceptions=False` is required: router stubs raise `NotImplementedError` which
    FastAPI propagates as an unhandled exception; this flag converts it to a 500 response instead
    of crashing the transport
- `db_session` — direct `TestingSessionLocal()` handle for asserting DB state after a request
  (e.g. inspecting `SourceExample` rows the upload route created)

## Test Files

| File | Scope |
|------|-------|
| `test_projects.py` | `/health` endpoint + full project create/list/get-by-id behavioral assertions |
| `test_datasets.py` | Dataset upload (CSV + JSONL, pointwise + pairwise expansion, validation, dedupe counts) and list assertions |
| `test_tasks.py` | Task generation and next-task route existence |
| `test_annotations.py` | Annotation submit and skip route existence |
| `test_consensus.py` | Pure-function unit tests for `compute_majority_vote`, `compute_agreement_score` plus DB-backed `compute_consensus` flow tests (full/partial agreement, model agree/disagree, latest-suggestion selection, label-key fallback, idempotent upsert, no-op cases, wrapper delegation) |
| `test_model_suggestions.py` | Route + service tests for `POST /tasks/{task_id}/suggestion`: cohere/local-fallback branching, Jaccard threshold mapping, `created → suggested` status transition (and non-transitions), 409 on terminal status, 404 on unknown task, 422 on missing payload fields, `lexical_overlap_score` pure-function unit tests, determinism |
| `test_exports.py` | Export create and status route existence |
| `test_relationships.py` | ORM relationship round-trip + `Project` cascade-delete down the Dataset → SourceExample → Task chain |
| `test_reviews.py` | Behavioral tests for `GET /projects/{project_id}/review/tasks` and `POST /tasks/{task_id}/review`: queue filter (only `needs_review` in target project, ordered newest-first, full detail shape with consensus block), submit (creates `ReviewDecision`, sets `Task.status='resolved'`, updates `ConsensusResult.final_label` + `status='review_resolved'`, emits `task.review_submitted` audit event), reviewer fallback (singleton system reviewer when `reviewer_id` is omitted), 422 on invalid `final_label`, 404 on unknown task / project / reviewer, 409 on resolved/exported and pre-review states |

## Conventions

- Route existence tests (stubbed routers): `assert response.status_code in (expected_2xx, 500)` — stubs return 500
- Behavioral tests (implemented routers, e.g. `projects`): assert exact status codes and response bodies
- Pure logic tests (consensus): import service function directly, no `client` fixture needed
- Do **not** mock the DB for route tests — `conftest.py` swaps in a SQLite test DB via `dependency_overrides[get_db]` and a JSONB→TEXT compile shim, so `TestClient` exercises the real app stack against ephemeral tables
