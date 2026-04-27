# backend/alembic/

Alembic migration environment for PostgreSQL. Run all commands from `backend/`.

## Commands

- **Apply all:** `alembic upgrade head`
- **New migration:** `alembic revision --autogenerate -m "add column foo to tasks"`
- **Downgrade one:** `alembic downgrade -1`
- **History:** `alembic history`
- **Current state:** `alembic current`

## Files

- `env.py` — imports `Base` from `app.db` and all models from `app.models`; supports `DATABASE_URL` env override
- `script.py.mako` — Mako template used when generating new migration files
- `versions/0001_initial_schema.py` — creates all 14 tables with FK constraints and check constraints

## Rules

- **Always** import new ORM models in `env.py` before running `--autogenerate`
- Migration files are **append-only** — never edit a migration that has been applied to any environment
- Use `postgresql.UUID`, `postgresql.JSONB` from `sqlalchemy.dialects.postgresql` (not generic SA types)
- Check constraints use named strings matching the ORM model's `__table_args__`
