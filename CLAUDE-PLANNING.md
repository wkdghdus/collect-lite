Before planning, inspect the existing repo structure and follow current conventions.

Important project alignment rules:
- Do not force the original MVP schema if the repo already has a better existing structure.
- Keep backend under backend/app unless the repo says otherwise.
- Preserve existing PostgreSQL UUID types; do not convert IDs to string UUIDs.
- Do not introduce Task.status="annotated". It is invalid.
- Use the existing task state machine:
  created → suggested → assigned → submitted → needs_review → resolved → exported
- Use "submitted" when enough annotations have been collected.
- Use "resolved" when consensus produces a final label.
- Use "needs_review" when consensus detects disagreement or low confidence.
- Keep Project.task_type as the source of truth. Do not add task_type to Task.
- Use SourceExample.payload JSON/JSONB for query, candidate_document, document_id, and metadata.
- Use assignment_id as the auth substitute for annotation submission. Derive annotator_id from Assignment.
- Prefer existing services, routers, schemas, tests, and dependency-injection style.
- Run ruff and pytest after backend changes. Report unrelated/pre-existing failures separately.