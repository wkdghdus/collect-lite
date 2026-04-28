import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.export import Export
from app.models.project import Project
from app.schemas.export import ExportCreate, ExportResponse
from app.workers import jobs

router = APIRouter(tags=["exports"])

CONTENT_TYPES = {
    "jsonl": "application/x-ndjson",
    "csv": "text/csv",
}


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportResponse,
    status_code=202,
)
def create_export(
    project_id: uuid.UUID,
    body: ExportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    export = Export(
        project_id=project_id,
        format=body.format,
        status="queued",
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    background_tasks.add_task(jobs.create_export, export.id)

    return export


@router.get(
    "/projects/{project_id}/exports",
    response_model=list[ExportResponse],
)
def list_exports(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return (
        db.query(Export)
        .filter(Export.project_id == project_id)
        .order_by(Export.created_at.desc())
        .all()
    )


@router.get("/exports/{export_id}", response_model=ExportResponse)
def get_export(export_id: uuid.UUID, db: Session = Depends(get_db)):
    export = db.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return export


@router.get("/exports/{export_id}/download")
def download_export(export_id: uuid.UUID, db: Session = Depends(get_db)):
    export = db.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.status != "completed":
        raise HTTPException(status_code=409, detail="Export not completed")
    if not export.file_path or not os.path.exists(export.file_path):
        raise HTTPException(status_code=410, detail="Export file missing")

    media_type = CONTENT_TYPES.get(export.format, "application/octet-stream")
    return FileResponse(
        path=export.file_path,
        media_type=media_type,
        filename=f"{export.id}.{export.format}",
    )
