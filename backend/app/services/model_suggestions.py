import re
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models.annotation import ModelSuggestion
from app.models.dataset import SourceExample
from app.models.task import Task
from app.services.cohere_service import (
    RERANK_MODEL,
    _score_to_label,
    generate_rerank_suggestion,
)

PROVIDER_COHERE = "cohere"
PROVIDER_LOCAL = "local"
MODEL_LOCAL_FALLBACK = "lexical_overlap"
TERMINAL_STATUSES = {"resolved", "exported"}

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


class TaskNotFoundError(LookupError):
    pass


class TaskTerminalError(RuntimeError):
    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(status)


class PayloadInvalidError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(",".join(missing))


def _tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")}


def lexical_overlap_score(query: str, document: str) -> float:
    """Jaccard overlap on lowercased alphanumeric tokens."""
    q = _tokenize(query)
    d = _tokenize(document)
    if not q or not d:
        return 0.0
    return len(q & d) / len(q | d)


def _local_suggestion(query: str, document: str) -> tuple[float, str, dict]:
    score = lexical_overlap_score(query, document)
    label = _score_to_label(score)
    return score, label, {"score": score, "method": "jaccard"}


def generate_suggestion_for_task(db: Session, task_id: uuid.UUID) -> ModelSuggestion:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise TaskNotFoundError(str(task_id))
    if task.status in TERMINAL_STATUSES:
        raise TaskTerminalError(task.status)

    example = db.query(SourceExample).filter(SourceExample.id == task.example_id).first()
    payload = example.payload if example else {}
    query = payload.get("query")
    document = payload.get("candidate_document")
    missing = [k for k, v in (("query", query), ("candidate_document", document)) if not v]
    if missing:
        raise PayloadInvalidError(missing)

    if settings.cohere_api_key:
        score, label, raw = generate_rerank_suggestion(query, document)
        provider, model_name = PROVIDER_COHERE, RERANK_MODEL
    else:
        score, label, raw = _local_suggestion(query, document)
        provider, model_name = PROVIDER_LOCAL, MODEL_LOCAL_FALLBACK

    suggestion = ModelSuggestion(
        task_id=task.id,
        provider=provider,
        model_name=model_name,
        suggestion={"relevance": label},
        confidence=score,
        raw_response=raw,
    )
    db.add(suggestion)

    if task.status == "created":
        task.status = "suggested"

    db.commit()
    db.refresh(suggestion)
    return suggestion
