import uuid

from app.models import (
    Annotation,
    Assignment,
    ConsensusResult,
    Dataset,
    ModelSuggestion,
    Project,
    ReviewDecision,
    SourceExample,
    Task,
    TaskTemplate,
    User,
)
from tests.conftest import TestingSessionLocal


def _build_chain(session):
    user = User(email=f"u-{uuid.uuid4()}@example.com", name="Tester", role="annotator")
    project = Project(name="Rel Project", task_type="classification")
    session.add_all([user, project])
    session.flush()

    dataset = Dataset(project_id=project.id, filename="data.jsonl", row_count=1)
    session.add(dataset)
    session.flush()

    example = SourceExample(
        dataset_id=dataset.id,
        project_id=project.id,
        source_hash=f"hash-{uuid.uuid4()}",
        payload={"text": "hello"},
    )
    template = TaskTemplate(
        project_id=project.id,
        name="Default",
        instructions="Label it",
        label_schema={"type": "string"},
    )
    session.add_all([example, template])
    session.flush()

    task = Task(
        project_id=project.id,
        example_id=example.id,
        template_id=template.id,
    )
    session.add(task)
    session.flush()

    assignment = Assignment(task_id=task.id, annotator_id=user.id)
    session.add(assignment)
    session.flush()

    annotation = Annotation(
        task_id=task.id,
        assignment_id=assignment.id,
        annotator_id=user.id,
        label={"value": "positive"},
    )
    session.add(annotation)
    session.commit()

    return {
        "user_id": user.id,
        "project_id": project.id,
        "dataset_id": dataset.id,
        "example_id": example.id,
        "task_id": task.id,
        "annotation_id": annotation.id,
    }


def test_relationship_round_trip() -> None:
    write_session = TestingSessionLocal()
    try:
        ids = _build_chain(write_session)
    finally:
        write_session.close()

    read_session = TestingSessionLocal()
    try:
        project = read_session.get(Project, ids["project_id"])
        assert project is not None
        assert len(project.datasets) == 1
        dataset = project.datasets[0]
        assert dataset.id == ids["dataset_id"]
        assert len(dataset.source_examples) == 1
        example = dataset.source_examples[0]
        assert example.id == ids["example_id"]
        assert len(example.tasks) == 1
        task = example.tasks[0]
        assert task.id == ids["task_id"]
        assert len(task.annotations) == 1
        annotation = task.annotations[0]
        assert annotation.id == ids["annotation_id"]
        assert annotation.task.id == task.id
        assert annotation.annotator.id == ids["user_id"]
    finally:
        read_session.close()


def test_project_cascade_delete() -> None:
    setup_session = TestingSessionLocal()
    try:
        ids = _build_chain(setup_session)

        task = setup_session.get(Task, ids["task_id"])
        suggestion = ModelSuggestion(
            task_id=task.id,
            provider="openai",
            model_name="gpt-x",
            suggestion={"value": "positive"},
        )
        consensus = ConsensusResult(
            task_id=task.id,
            final_label={"value": "positive"},
            agreement_score=1.0,
            method="majority",
            num_annotations=1,
            status="auto_resolved",
        )
        review = ReviewDecision(
            task_id=task.id,
            reviewer_id=ids["user_id"],
            final_label={"value": "positive"},
        )
        setup_session.add_all([suggestion, consensus, review])
        setup_session.commit()
    finally:
        setup_session.close()

    delete_session = TestingSessionLocal()
    try:
        project = delete_session.get(Project, ids["project_id"])
        assert project is not None
        delete_session.delete(project)
        delete_session.commit()
    finally:
        delete_session.close()

    verify_session = TestingSessionLocal()
    try:
        assert verify_session.query(Project).count() == 0
        assert verify_session.query(Dataset).count() == 0
        assert verify_session.query(SourceExample).count() == 0
        assert verify_session.query(Task).count() == 0
        assert verify_session.query(Annotation).count() == 0
        assert verify_session.query(ModelSuggestion).count() == 0
        assert verify_session.query(ConsensusResult).count() == 0
        assert verify_session.query(ReviewDecision).count() == 0
        assert verify_session.query(User).filter(User.id == ids["user_id"]).count() == 1
    finally:
        verify_session.close()
