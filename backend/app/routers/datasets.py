import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.dataset import Dataset, SourceExample
from app.models.project import Project
from app.schemas.dataset import DatasetResponse, DatasetUploadResponse
from app.services.ingestion import (
    example_source_hash,
    normalize_rows,
    parse_upload,
)

router = APIRouter(tags=["datasets"])


@router.post(
    "/projects/{project_id}/datasets",
    response_model=DatasetUploadResponse,
    status_code=201,
)
async def upload_dataset(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    try:
        rows = parse_upload(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"parse error: {exc}") from exc

    examples, errors = normalize_rows(rows)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    seen_hashes: set[str] = set()
    deduped: list[dict] = []
    skipped_in_file = 0
    for example in examples:
        source_hash = example_source_hash(example)
        if source_hash in seen_hashes:
            skipped_in_file += 1
            continue
        seen_hashes.add(source_hash)
        example["source_hash"] = source_hash
        deduped.append(example)

    if seen_hashes:
        existing_hashes = {
            row[0]
            for row in db.query(SourceExample.source_hash)
            .filter(
                SourceExample.project_id == project_id,
                SourceExample.source_hash.in_(seen_hashes),
            )
            .all()
        }
    else:
        existing_hashes = set()
    to_insert = [ex for ex in deduped if ex["source_hash"] not in existing_hashes]
    existing_dup_count = len(deduped) - len(to_insert)

    dataset = Dataset(
        project_id=project_id,
        filename=file.filename or "upload",
        row_count=len(to_insert),
        status="uploaded",
    )
    db.add(dataset)
    db.flush()
    for example in to_insert:
        db.add(
            SourceExample(
                dataset_id=dataset.id,
                project_id=project_id,
                external_id=example["document_id"],
                source_hash=example["source_hash"],
                payload={
                    "query": example["query"],
                    "candidate_document": example["candidate_document"],
                    "document_id": example["document_id"],
                    "metadata": example.get("metadata"),
                },
            )
        )
    db.commit()
    db.refresh(dataset)

    return DatasetUploadResponse(
        id=dataset.id,
        project_id=dataset.project_id,
        filename=dataset.filename,
        schema_version=dataset.schema_version,
        row_count=dataset.row_count,
        status=dataset.status,
        created_at=dataset.created_at,
        inserted_count=len(to_insert),
        skipped_duplicate_count=skipped_in_file,
        existing_duplicate_count=existing_dup_count,
        total_input_rows=len(rows),
        total_normalized_examples=len(examples),
    )


@router.get("/projects/{project_id}/datasets", response_model=list[DatasetResponse])
def list_datasets(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return (
        db.query(Dataset)
        .filter(Dataset.project_id == project_id)
        .order_by(Dataset.created_at.desc())
        .all()
    )


@router.get("/datasets/{dataset_id}/errors")
def get_dataset_errors(dataset_id: uuid.UUID, db: Session = Depends(get_db)):
    raise NotImplementedError
