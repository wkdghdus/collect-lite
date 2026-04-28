import csv
import io
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models.annotation import ModelSuggestion
from app.models.export import Export
from app.models.quality import ReviewDecision
from app.models.task import Task

logger = logging.getLogger(__name__)

LABEL_KEY = "relevance"
LABEL_KEY_FALLBACK = "label"
PAYLOAD_TOP_KEYS = ("query", "candidate_document", "document_id")
CSV_HEADER = [
    "query",
    "candidate_document",
    "document_id",
    "final_label",
    "label_source",
    "model_suggestion",
    "model_score",
    "human_agreement",
    "metadata",
]


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _read_label(label_dict: dict) -> Any:
    if LABEL_KEY in label_dict:
        return label_dict[LABEL_KEY]
    return label_dict.get(LABEL_KEY_FALLBACK)


def _collect_export_rows(db: Session, project_id: uuid.UUID) -> tuple[list[Task], list[dict]]:
    tasks = (
        db.query(Task)
        .options(
            selectinload(Task.example),
            selectinload(Task.consensus_results),
            selectinload(Task.model_suggestions),
        )
        .filter(Task.project_id == project_id, Task.status == "resolved")
        .order_by(Task.created_at.asc())
        .all()
    )

    included: list[Task] = []
    rows: list[dict] = []
    for task in tasks:
        consensus_rows = sorted(
            task.consensus_results or [],
            key=lambda c: c.created_at,
            reverse=True,
        )
        if not consensus_rows:
            continue
        consensus = consensus_rows[0]

        suggestion_rows = sorted(
            task.model_suggestions or [],
            key=lambda s: s.created_at,
            reverse=True,
        )
        latest_suggestion: ModelSuggestion | None = suggestion_rows[0] if suggestion_rows else None

        review_exists = (
            db.query(ReviewDecision.id).filter(ReviewDecision.task_id == task.id).first()
            is not None
        )

        payload = _as_dict(task.example.payload if task.example else {})
        metadata = {k: v for k, v in payload.items() if k not in PAYLOAD_TOP_KEYS}

        suggestion_dict = _as_dict(latest_suggestion.suggestion) if latest_suggestion else {}
        model_suggestion_label = _read_label(suggestion_dict) if latest_suggestion else None
        model_score = (
            float(latest_suggestion.confidence)
            if latest_suggestion is not None and latest_suggestion.confidence is not None
            else None
        )

        rows.append(
            {
                "query": payload.get("query"),
                "candidate_document": payload.get("candidate_document"),
                "document_id": payload.get("document_id"),
                "final_label": _read_label(_as_dict(consensus.final_label)),
                "label_source": "review" if review_exists else "consensus",
                "model_suggestion": model_suggestion_label,
                "model_score": model_score,
                "human_agreement": float(consensus.agreement_score),
                "metadata": metadata,
            }
        )
        included.append(task)

    return included, rows


def _serialize_jsonl(rows: list[dict]) -> str:
    if not rows:
        return ""
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"


def _serialize_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    for row in rows:
        writer.writerow(
            [
                "" if row["query"] is None else row["query"],
                "" if row["candidate_document"] is None else row["candidate_document"],
                "" if row["document_id"] is None else row["document_id"],
                "" if row["final_label"] is None else row["final_label"],
                row["label_source"],
                "" if row["model_suggestion"] is None else row["model_suggestion"],
                "" if row["model_score"] is None else row["model_score"],
                row["human_agreement"],
                json.dumps(row["metadata"], ensure_ascii=False),
            ]
        )
    return output.getvalue()


def generate_jsonl_export(db: Session, project_id: uuid.UUID) -> tuple[str, int]:
    _, rows = _collect_export_rows(db, project_id)
    return _serialize_jsonl(rows), len(rows)


def generate_csv_export(db: Session, project_id: uuid.UUID) -> tuple[str, int]:
    _, rows = _collect_export_rows(db, project_id)
    return _serialize_csv(rows), len(rows)


_FORMAT_SERIALIZERS = {
    "jsonl": _serialize_jsonl,
    "csv": _serialize_csv,
}


def _resolve_exports_dir() -> Path:
    return Path(settings.exports_dir).resolve()


def run_export_job(db: Session, export_id: uuid.UUID) -> None:
    export = db.query(Export).filter(Export.id == export_id).first()
    if export is None:
        return

    serializer = _FORMAT_SERIALIZERS.get(export.format)
    if serializer is None:
        export.status = "failed"
        db.commit()
        return

    file_path: Path | None = None
    try:
        export.status = "running"
        db.commit()

        included, rows = _collect_export_rows(db, export.project_id)
        content = serializer(rows)

        exports_dir = _resolve_exports_dir()
        exports_dir.mkdir(parents=True, exist_ok=True)
        file_path = exports_dir / f"{export.id}.{export.format}"
        file_path.write_text(content, encoding="utf-8")

        for task in included:
            task.status = "exported"

        export.status = "completed"
        export.file_path = str(file_path)
        export.row_count = len(rows)
        db.commit()
    except Exception:
        logger.exception("Export job %s failed", export_id)
        db.rollback()
        if file_path is not None and file_path.exists():
            try:
                os.remove(file_path)
            except OSError:
                logger.exception("Failed to remove partial export file %s", file_path)
        export = db.query(Export).filter(Export.id == export_id).first()
        if export is not None:
            export.status = "failed"
            export.file_path = None
            db.commit()
