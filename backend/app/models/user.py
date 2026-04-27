import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    annotations: Mapped[list["Annotation"]] = relationship(
        back_populates="annotator",
        lazy="selectin",
    )
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        back_populates="reviewer",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'owner', 'annotator', 'reviewer')", name="users_role_check"
        ),
    )
