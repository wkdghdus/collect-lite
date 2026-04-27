import csv
import io
import json
import uuid
from sqlalchemy.orm import Session


def generate_jsonl_export(db: Session, project_id: uuid.UUID) -> str:
    """Build a JSONL string from resolved tasks for a project."""
    return ""


def generate_csv_export(db: Session, project_id: uuid.UUID) -> str:
    """Build a CSV string from resolved tasks for a project."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["example_id", "final_label", "agreement_score", "num_annotations", "split"])
    return output.getvalue()


def run_export_job(db: Session, export_id: uuid.UUID) -> None:
    """Background job: generate export file and update Export record."""
    pass
