import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    format: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("format IN ('jsonl', 'csv')", name="exports_format_check"),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')", name="exports_status_check"
        ),
    )
