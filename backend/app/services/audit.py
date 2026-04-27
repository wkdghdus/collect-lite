import uuid
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def log_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
