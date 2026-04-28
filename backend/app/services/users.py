from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User

DEMO_ANNOTATORS: list[dict[str, str]] = [
    {"email": "alice@collectlite.local", "name": "Alice Annotator"},
    {"email": "bob@collectlite.local", "name": "Bob Annotator"},
]


def ensure_demo_annotators(db: Session) -> list[User]:
    users: list[User] = []
    for spec in DEMO_ANNOTATORS:
        user = db.query(User).filter(User.email == spec["email"]).first()
        if user is None:
            user = User(email=spec["email"], name=spec["name"], role="annotator")
            db.add(user)
            db.flush()
        users.append(user)
    return users
