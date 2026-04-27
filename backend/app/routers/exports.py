import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.export import ExportCreate, ExportResponse

router = APIRouter(tags=["exports"])


@router.post("/projects/{project_id}/exports", response_model=ExportResponse, status_code=202)
def create_export(project_id: uuid.UUID, body: ExportCreate, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/exports/{export_id}", response_model=ExportResponse)
def get_export(export_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/exports/{export_id}/download")
def download_export(export_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
