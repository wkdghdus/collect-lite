import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.dataset import DatasetResponse

router = APIRouter(tags=["datasets"])


@router.post("/projects/{project_id}/datasets", response_model=DatasetResponse, status_code=201)
async def upload_dataset(project_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/projects/{project_id}/datasets", response_model=list[DatasetResponse])
def list_datasets(project_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError


@router.get("/datasets/{dataset_id}/errors")
def get_dataset_errors(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
