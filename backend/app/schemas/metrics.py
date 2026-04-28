from pydantic import BaseModel


class ProjectMetricsResponse(BaseModel):
    total_tasks: int
    created_count: int
    suggested_count: int
    assigned_count: int
    submitted_count: int
    needs_review_count: int
    resolved_count: int
    exported_count: int
    avg_human_agreement: float | None
    model_human_agreement_rate: float | None
    final_label_distribution: dict[str, int]
    exportable_task_count: int
