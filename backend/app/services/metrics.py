import uuid
from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.annotation import ModelSuggestion
from app.models.quality import ConsensusResult
from app.models.task import Task
from app.services.consensus import LABEL_KEY, _read_suggestion_label

TASK_STATUSES = (
    "created",
    "suggested",
    "assigned",
    "submitted",
    "needs_review",
    "resolved",
    "exported",
)


def compute_project_metrics(db: Session, project_id: uuid.UUID) -> dict:
    counts = {status: 0 for status in TASK_STATUSES}
    status_rows = (
        db.query(Task.status, func.count(Task.id))
        .filter(Task.project_id == project_id)
        .group_by(Task.status)
        .all()
    )
    for status, n in status_rows:
        if status in counts:
            counts[status] = n
    total_tasks = sum(counts.values())

    latest_consensus_subq = (
        db.query(
            ConsensusResult.task_id.label("task_id"),
            func.max(ConsensusResult.created_at).label("max_created"),
        )
        .join(Task, Task.id == ConsensusResult.task_id)
        .filter(Task.project_id == project_id)
        .group_by(ConsensusResult.task_id)
        .subquery()
    )
    consensus_rows = (
        db.query(ConsensusResult)
        .join(
            latest_consensus_subq,
            (ConsensusResult.task_id == latest_consensus_subq.c.task_id)
            & (ConsensusResult.created_at == latest_consensus_subq.c.max_created),
        )
        .all()
    )

    if consensus_rows:
        avg_human_agreement = sum(float(r.agreement_score) for r in consensus_rows) / len(
            consensus_rows
        )
    else:
        avg_human_agreement = None

    distribution: Counter = Counter()
    for r in consensus_rows:
        value = r.final_label.get(LABEL_KEY) if isinstance(r.final_label, dict) else None
        if value is not None:
            distribution[value] += 1

    consensus_by_task = {r.task_id: r for r in consensus_rows}
    matches = 0
    denom = 0
    if consensus_by_task:
        latest_suggestion_subq = (
            db.query(
                ModelSuggestion.task_id.label("task_id"),
                func.max(ModelSuggestion.created_at).label("max_created"),
            )
            .filter(ModelSuggestion.task_id.in_(consensus_by_task.keys()))
            .group_by(ModelSuggestion.task_id)
            .subquery()
        )
        suggestion_rows = (
            db.query(ModelSuggestion)
            .join(
                latest_suggestion_subq,
                (ModelSuggestion.task_id == latest_suggestion_subq.c.task_id)
                & (ModelSuggestion.created_at == latest_suggestion_subq.c.max_created),
            )
            .all()
        )
        for s in suggestion_rows:
            consensus = consensus_by_task[s.task_id]
            denom += 1
            human_label = (
                consensus.final_label.get(LABEL_KEY)
                if isinstance(consensus.final_label, dict)
                else None
            )
            model_label = _read_suggestion_label(s.suggestion)
            if human_label is not None and human_label == model_label:
                matches += 1
    model_human_agreement_rate = matches / denom if denom > 0 else None

    return {
        "total_tasks": total_tasks,
        "created_count": counts["created"],
        "suggested_count": counts["suggested"],
        "assigned_count": counts["assigned"],
        "submitted_count": counts["submitted"],
        "needs_review_count": counts["needs_review"],
        "resolved_count": counts["resolved"],
        "exported_count": counts["exported"],
        "avg_human_agreement": avg_human_agreement,
        "model_human_agreement_rate": model_human_agreement_rate,
        "final_label_distribution": dict(distribution),
        "exportable_task_count": counts["resolved"],
    }
