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

## Test Files

| File | Scope |
|------|-------|
| `test_projects.py` | `/health` endpoint + project CRUD route existence |
| `test_datasets.py` | Dataset upload and list route existence |
| `test_tasks.py` | Task generation and next-task route existence |
| `test_annotations.py` | Annotation submit and skip route existence |
| `test_consensus.py` | Pure-function unit tests for `compute_majority_vote`, `compute_agreement_score` |
| `test_exports.py` | Export create and status route existence |
| `test_relationships.py` | ORM relationship round-trip + `Project` cascade-delete down the Dataset → SourceExample → Task chain |

## Conventions

- Route existence tests: `assert response.status_code in (expected_2xx, 500)` — stubs return 500
- Pure logic tests (consensus): import service function directly, no `client` fixture needed
- Do **not** mock the DB for route tests — `TestClient` exercises the real app stack
