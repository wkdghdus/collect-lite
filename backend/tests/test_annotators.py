from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User


def test_annotators_endpoint_returns_two(client: TestClient) -> None:
    response = client.get("/api/annotators")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2
    emails = {row["email"] for row in body}
    assert emails == {"alice@collectlite.local", "bob@collectlite.local"}
    for row in body:
        assert row["role"] == "annotator"
        for field in ("id", "email", "name", "role", "created_at"):
            assert field in row


def test_annotators_endpoint_is_idempotent(
    client: TestClient, db_session: Session
) -> None:
    first = client.get("/api/annotators").json()
    second = client.get("/api/annotators").json()
    third = client.get("/api/annotators").json()

    first_ids = [row["id"] for row in first]
    second_ids = [row["id"] for row in second]
    third_ids = [row["id"] for row in third]
    assert first_ids == second_ids == third_ids

    db_session.expire_all()
    annotator_count = (
        db_session.query(User)
        .filter(
            User.email.in_(
                ["alice@collectlite.local", "bob@collectlite.local"]
            )
        )
        .count()
    )
    assert annotator_count == 2


def test_annotators_endpoint_reuses_existing_users(
    client: TestClient, db_session: Session
) -> None:
    """If alice and bob already exist (e.g. seeded), the endpoint reuses them."""
    pre_alice = User(
        email="alice@collectlite.local",
        name="Alice Annotator",
        role="annotator",
    )
    pre_bob = User(
        email="bob@collectlite.local",
        name="Bob Annotator",
        role="annotator",
    )
    db_session.add_all([pre_alice, pre_bob])
    db_session.commit()
    pre_alice_id = pre_alice.id
    pre_bob_id = pre_bob.id

    response = client.get("/api/annotators")
    assert response.status_code == 200
    body = response.json()
    by_email = {row["email"]: row["id"] for row in body}
    assert by_email["alice@collectlite.local"] == str(pre_alice_id)
    assert by_email["bob@collectlite.local"] == str(pre_bob_id)
