"""Add updated_at column to annotations

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-28
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "annotations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Backfill so the initial value matches created_at rather than the migration moment.
    op.execute("UPDATE annotations SET updated_at = created_at")


def downgrade() -> None:
    op.drop_column("annotations", "updated_at")
