import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.project import Project
from app.schemas.metrics import ProjectMetricsResponse
from app.services.metrics import compute_project_metrics

router = APIRouter(tags=["metrics"])


@router.get("/projects/{project_id}/metrics", response_model=ProjectMetricsResponse)
def get_project_metrics(
    project_id: uuid.UUID, db: Session = Depends(get_db)
) -> ProjectMetricsResponse:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    payload = compute_project_metrics(db, project_id)
    return ProjectMetricsResponse(**payload)
