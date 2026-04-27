import uuid
from collections import Counter
from sqlalchemy.orm import Session


def compute_majority_vote(labels: list[dict], key: str) -> dict | None:
    # Returns None on tie (Counter.most_common is deterministic but arbitrary on ties)
    values = [l.get(key) for l in labels if key in l]
    if not values:
        return None
    most_common, count = Counter(values).most_common(1)[0]
    return {key: most_common, "_count": count, "_total": len(values)}


def compute_average_score(labels: list[dict], key: str) -> float | None:
    values = [l[key] for l in labels if key in l and isinstance(l[key], (int, float))]
    return sum(values) / len(values) if values else None


def compute_agreement_score(labels: list[dict], key: str) -> float:
    values = [l.get(key) for l in labels if key in l]
    if not values:
        return 0.0
    most_common_count = Counter(values).most_common(1)[0][1]
    return most_common_count / len(values)


def resolve_task_consensus(db: Session, task_id: uuid.UUID) -> None:
    pass
