import uuid
from collections import Counter

from sqlalchemy.orm import Session

from app.models.annotation import Annotation, ModelSuggestion
from app.models.quality import ConsensusResult
from app.models.task import Task

LABEL_KEY = "relevance"
LABEL_KEY_FALLBACK = "label"
METHOD_MAJORITY = "majority_vote"


def compute_majority_vote(labels: list[dict], key: str) -> dict | None:
    # Returns None on tie (Counter.most_common is deterministic but arbitrary on ties)
    values = [lab.get(key) for lab in labels if key in lab]
    if not values:
        return None
    most_common, count = Counter(values).most_common(1)[0]
    return {key: most_common, "_count": count, "_total": len(values)}


def compute_average_score(labels: list[dict], key: str) -> float | None:
    values = [lab[key] for lab in labels if key in lab and isinstance(lab[key], (int, float))]
    return sum(values) / len(values) if values else None


def compute_agreement_score(labels: list[dict], key: str) -> float:
    values = [lab.get(key) for lab in labels if key in lab]
    if not values:
        return 0.0
    most_common_count = Counter(values).most_common(1)[0][1]
    return most_common_count / len(values)


def _read_suggestion_label(suggestion: dict | None) -> str | None:
    if not suggestion:
        return None
    value = suggestion.get(LABEL_KEY)
    if value is None:
        value = suggestion.get(LABEL_KEY_FALLBACK)
    return value


def compute_consensus(db: Session, task_id: uuid.UUID) -> None:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        return

    annotations = db.query(Annotation).filter(Annotation.task_id == task_id).all()
    if not annotations:
        return
    if len(annotations) < task.required_annotations:
        return

    labels = [a.label for a in annotations]
    majority = compute_majority_vote(labels, LABEL_KEY)
    if majority is None:
        return

    majority_label = majority[LABEL_KEY]
    majority_count = majority["_count"]
    total = len(annotations)
    human_agreement = majority_count / total

    latest_suggestion = (
        db.query(ModelSuggestion)
        .filter(ModelSuggestion.task_id == task_id)
        .order_by(ModelSuggestion.created_at.desc())
        .first()
    )
    if latest_suggestion is None:
        model_agreement = None
    else:
        suggested_label = _read_suggestion_label(latest_suggestion.suggestion)
        model_agreement = suggested_label == majority_label

    requires_review = human_agreement < 1.0 or model_agreement is False

    # Follow-up (not required now): add UNIQUE(task_id) on consensus_results and
    # replace the read-then-update/insert below with an ON CONFLICT (task_id) DO UPDATE
    # upsert. The current path is safe because FastAPI BackgroundTasks runs serially
    # per request, but a concurrent caller could race and produce duplicate rows.
    existing = (
        db.query(ConsensusResult)
        .filter(ConsensusResult.task_id == task_id)
        .order_by(ConsensusResult.created_at.desc())
        .first()
    )
    payload = dict(
        final_label={LABEL_KEY: majority_label},
        agreement_score=human_agreement,
        method=METHOD_MAJORITY,
        num_annotations=total,
        status="needs_review" if requires_review else "auto_resolved",
    )
    if existing is None:
        db.add(ConsensusResult(task_id=task_id, **payload))
    else:
        for k, v in payload.items():
            setattr(existing, k, v)

    task.status = "needs_review" if requires_review else "resolved"
    db.commit()


def resolve_task_consensus(db: Session, task_id: uuid.UUID) -> None:
    compute_consensus(db, task_id)
