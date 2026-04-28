"""Seed script: produces a demo-ready CollectLite project in one idempotent run.

Run from `backend/`:

    python -m scripts.seed                          # full demo (default)
    python -m scripts.seed --no-suggestions         # skip model suggestions
    python -m scripts.seed --no-annotations         # skip annotation walk
    python -m scripts.seed --sample-path /path.jsonl

Idempotency: rerunning the same command on an already-seeded database adds
zero rows.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.annotation import Annotation, ModelSuggestion
from app.models.dataset import Dataset, SourceExample
from app.models.project import Project
from app.models.task import Assignment, Task, TaskTemplate
from app.models.user import User
from app.services import consensus as consensus_service
from app.services import model_suggestions as model_suggestions_service
from app.services import review as review_service
from app.services.ingestion import (
    example_source_hash,
    normalize_rows,
    parse_jsonl,
)
from app.services.task_generation import generate_tasks_for_project

PROJECT_NAME = "RAG Relevance Demo"
PROJECT_TASK_TYPE = "rag_relevance"
TEMPLATE_NAME = "RAG Relevance v1"
DATASET_FILENAME_PREFIX = "seed:"

LABEL_RELEVANT = "relevant"
LABEL_PARTIALLY_RELEVANT = "partially_relevant"
LABEL_NOT_RELEVANT = "not_relevant"
LABEL_OPTIONS = [LABEL_RELEVANT, LABEL_PARTIALLY_RELEVANT, LABEL_NOT_RELEVANT]

DEFAULT_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_relevance_tasks.jsonl"

DEMO_USERS = [
    {
        "email": "owner@collectlite.local",
        "name": "Demo Owner",
        "role": "owner",
    },
    {
        "email": "alice@collectlite.local",
        "name": "Alice Annotator",
        "role": "annotator",
    },
    {
        "email": "bob@collectlite.local",
        "name": "Bob Annotator",
        "role": "annotator",
    },
    {
        "email": "carol@collectlite.local",
        "name": "Carol Reviewer",
        "role": "reviewer",
    },
]


@dataclass
class SeedReport:
    users: int = 0
    projects: int = 0
    datasets: int = 0
    source_examples: int = 0
    templates: int = 0
    tasks: int = 0
    suggestions: int = 0
    assignments: int = 0
    annotations: int = 0
    consensus_results: int = 0
    review_decisions: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def total_created(self) -> int:
        return (
            self.users
            + self.projects
            + self.datasets
            + self.source_examples
            + self.templates
            + self.tasks
            + self.suggestions
            + self.assignments
            + self.annotations
            + self.consensus_results
            + self.review_decisions
        )

    def format(self) -> str:
        lines = [
            "Seed summary (rows created this run):",
            f"  users:             {self.users}",
            f"  projects:          {self.projects}",
            f"  datasets:          {self.datasets}",
            f"  source_examples:   {self.source_examples}",
            f"  task_templates:    {self.templates}",
            f"  tasks:             {self.tasks}",
            f"  model_suggestions: {self.suggestions}",
            f"  assignments:       {self.assignments}",
            f"  annotations:       {self.annotations}",
            f"  consensus_results: {self.consensus_results}",
            f"  review_decisions:  {self.review_decisions}",
        ]
        if self.notes:
            lines.append("Notes:")
            lines.extend(f"  - {note}" for note in self.notes)
        if self.total_created == 0:
            lines.append("Re-run safe: 0 new rows.")
        return "\n".join(lines)


def _ensure_user(db: Session, *, email: str, name: str, role: str) -> tuple[User, bool]:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        return existing, False
    user = User(email=email, name=name, role=role)
    db.add(user)
    db.flush()
    return user, True


def _ensure_users(db: Session, report: SeedReport) -> dict[str, User]:
    by_email: dict[str, User] = {}
    for spec in DEMO_USERS:
        user, created = _ensure_user(db, **spec)
        by_email[spec["email"]] = user
        if created:
            report.users += 1
    return by_email


def _ensure_project(db: Session, *, owner_id, report: SeedReport) -> Project:
    existing = db.query(Project).filter(Project.name == PROJECT_NAME).first()
    if existing is not None:
        return existing
    project = Project(
        name=PROJECT_NAME,
        description=(
            "Demo RAG relevance evaluation: rate retrieved documents against "
            "a query as relevant, partially relevant, or not relevant."
        ),
        owner_id=owner_id,
        task_type=PROJECT_TASK_TYPE,
        status="active",
    )
    db.add(project)
    db.flush()
    report.projects += 1
    return project


def _ensure_dataset_and_examples(
    db: Session,
    project: Project,
    sample_path: Path,
    report: SeedReport,
) -> None:
    filename = f"{DATASET_FILENAME_PREFIX}{sample_path.name}"

    raw_rows = parse_jsonl(sample_path.read_bytes())
    examples, errors = normalize_rows(raw_rows)
    if errors:
        report.notes.append(
            f"normalize_rows reported {len(errors)} row error(s); skipping those rows"
        )

    seen_hashes: set[str] = set()
    deduped: list[dict] = []
    for example in examples:
        source_hash = example_source_hash(example)
        if source_hash in seen_hashes:
            continue
        seen_hashes.add(source_hash)
        example["source_hash"] = source_hash
        deduped.append(example)

    if seen_hashes:
        existing_hashes = {
            row[0]
            for row in db.query(SourceExample.source_hash)
            .filter(
                SourceExample.project_id == project.id,
                SourceExample.source_hash.in_(seen_hashes),
            )
            .all()
        }
    else:
        existing_hashes = set()

    to_insert = [ex for ex in deduped if ex["source_hash"] not in existing_hashes]

    dataset = (
        db.query(Dataset)
        .filter(Dataset.project_id == project.id, Dataset.filename == filename)
        .first()
    )
    if dataset is None:
        dataset = Dataset(
            project_id=project.id,
            filename=filename,
            row_count=len(to_insert),
            status="validated",
        )
        db.add(dataset)
        db.flush()
        report.datasets += 1

    for example in to_insert:
        db.add(
            SourceExample(
                dataset_id=dataset.id,
                project_id=project.id,
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
        report.source_examples += 1

    db.flush()


def _ensure_template(db: Session, project: Project, report: SeedReport) -> TaskTemplate:
    existing = (
        db.query(TaskTemplate)
        .filter(TaskTemplate.project_id == project.id, TaskTemplate.name == TEMPLATE_NAME)
        .first()
    )
    if existing is not None:
        return existing
    template = TaskTemplate(
        project_id=project.id,
        name=TEMPLATE_NAME,
        instructions=(
            "Read the query and the candidate document. Mark the document "
            "'relevant' if it directly answers the query, 'partially_relevant' "
            "if it touches the same topic but does not answer the question, or "
            "'not_relevant' if it is off-topic."
        ),
        label_schema={
            "type": "single_choice",
            "field": "relevance",
            "options": LABEL_OPTIONS,
        },
        version=1,
    )
    db.add(template)
    db.flush()
    report.templates += 1
    return template


def _ensure_tasks(
    db: Session, project: Project, template: TaskTemplate, report: SeedReport
) -> None:
    report.tasks += generate_tasks_for_project(db, project.id, template.id, required_annotations=2)


def _ensure_suggestions(db: Session, project: Project, report: SeedReport) -> None:
    tasks: Iterable[Task] = (
        db.query(Task).filter(Task.project_id == project.id, Task.status == "created").all()
    )
    for task in tasks:
        try:
            model_suggestions_service.generate_suggestion_for_task(db, task.id)
            report.suggestions += 1
        except model_suggestions_service.TaskTerminalError:
            continue
        except model_suggestions_service.PayloadInvalidError as exc:
            report.notes.append(
                f"skipped suggestion for task {task.id}: missing {','.join(exc.missing)}"
            )


def _disagreement_indices(total: int, *, every: int = 4) -> set[int]:
    """Pick deterministic indices that should produce annotation disagreement.

    Always yields at least 2 indices when total >= 2 so the demo dashboard
    has both resolved and needs_review tasks.
    """
    indices = {i for i in range(total) if i % every == 0}
    if len(indices) < 2 and total >= 2:
        indices = {0, total // 2}
    return indices


def _ensure_annotations_and_consensus(
    db: Session,
    project: Project,
    annotators: list[User],
    reviewer: User,
    report: SeedReport,
) -> None:
    if len(annotators) < 2:
        raise ValueError("seed requires at least 2 annotators for the demo walk")
    annotator_a, annotator_b = annotators[0], annotators[1]

    eligible_statuses = {"created", "suggested"}
    tasks = (
        db.query(Task)
        .join(SourceExample, SourceExample.id == Task.example_id)
        .filter(Task.project_id == project.id, Task.status.in_(eligible_statuses))
        .order_by(SourceExample.external_id.asc(), Task.id.asc())
        .all()
    )
    if not tasks:
        return

    disagreement = _disagreement_indices(len(tasks))

    for idx, task in enumerate(tasks):
        latest_suggestion = (
            db.query(ModelSuggestion)
            .filter(ModelSuggestion.task_id == task.id)
            .order_by(ModelSuggestion.created_at.desc())
            .first()
        )
        model_label = (
            (latest_suggestion.suggestion or {}).get("relevance")
            if latest_suggestion is not None
            else None
        )

        if idx in disagreement or model_label not in LABEL_OPTIONS:
            label_a, label_b = LABEL_RELEVANT, LABEL_PARTIALLY_RELEVANT
        else:
            label_a = label_b = model_label

        for user, label in ((annotator_a, label_a), (annotator_b, label_b)):
            assignment = Assignment(
                task_id=task.id,
                annotator_id=user.id,
                status="submitted",
                started_at=task.created_at,
                submitted_at=task.created_at,
            )
            db.add(assignment)
            db.flush()
            report.assignments += 1

            db.add(
                Annotation(
                    task_id=task.id,
                    assignment_id=assignment.id,
                    annotator_id=user.id,
                    label={"relevance": label},
                    confidence=4,
                    notes="seed",
                )
            )
            report.annotations += 1

        task.status = "submitted"
        db.flush()

        consensus_service.compute_consensus(db, task.id)
        report.consensus_results += 1

    review_target = (
        db.query(Task)
        .filter(Task.project_id == project.id, Task.status == "needs_review")
        .order_by(Task.created_at.asc(), Task.id.asc())
        .first()
    )
    if review_target is not None:
        review_service.submit_review_decision(
            db,
            task_id=review_target.id,
            final_label=LABEL_RELEVANT,
            reason="seed: reviewer override",
            reviewer_id=reviewer.id,
        )
        db.commit()
        report.review_decisions += 1


def seed(
    *,
    sample_path: Path = DEFAULT_SAMPLE_PATH,
    with_suggestions: bool = True,
    with_annotations: bool = True,
    session: Session | None = None,
) -> SeedReport:
    db = session or SessionLocal()
    owns_session = session is None
    report = SeedReport()
    try:
        users_by_email = _ensure_users(db, report)
        owner = users_by_email["owner@collectlite.local"]
        annotators = [
            users_by_email["alice@collectlite.local"],
            users_by_email["bob@collectlite.local"],
        ]
        reviewer = users_by_email["carol@collectlite.local"]
        db.commit()

        project = _ensure_project(db, owner_id=owner.id, report=report)
        db.commit()

        _ensure_dataset_and_examples(db, project, sample_path, report)
        db.commit()

        template = _ensure_template(db, project, report)
        db.commit()

        _ensure_tasks(db, project, template, report)

        if with_suggestions:
            _ensure_suggestions(db, project, report)

        if with_annotations:
            _ensure_annotations_and_consensus(db, project, annotators, reviewer, report)
    finally:
        if owns_session:
            db.close()
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-path",
        type=Path,
        default=DEFAULT_SAMPLE_PATH,
        help="JSONL file with relevance examples (pointwise or pairwise).",
    )
    parser.add_argument(
        "--no-suggestions",
        action="store_true",
        help="Skip generating model suggestions for each task.",
    )
    parser.add_argument(
        "--no-annotations",
        action="store_true",
        help="Skip seeding human annotations, consensus, and the review decision.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = seed(
        sample_path=args.sample_path,
        with_suggestions=not args.no_suggestions,
        with_annotations=not args.no_annotations,
    )
    print(report.format())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
