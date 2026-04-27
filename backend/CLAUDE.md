# backend/

FastAPI + Python 3.11. Entry point: `app/main.py` → http://localhost:8000

## Commands

- **Install:** `pip install -e ".[dev]"` (use `.venv/bin/pip` if inside a venv)
- **Run:** `uvicorn app.main:app --reload --port 8000`
- **API docs:** http://localhost:8000/docs (Swagger UI, auto-generated)
- **Migrate:** `alembic upgrade head`
- **New migration:** `alembic revision --autogenerate -m "description"`
- **Test:** `pytest tests/ -v`
- **Lint:** `ruff check .`
- **Format:** `black .`

## Directory Structure

- `app/` — FastAPI application package (see `app/CLAUDE.md`)
- `alembic/` — migration scripts (see `alembic/CLAUDE.md`)
- `tests/` — pytest suite (see `tests/CLAUDE.md`)

## Env Vars

Loaded from `.env` via `app/config.py` (pydantic-settings).

| Var | Format |
|-----|--------|
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/dbname` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `COHERE_API_KEY` | string |
| `SECRET_KEY` | string (change in production) |
