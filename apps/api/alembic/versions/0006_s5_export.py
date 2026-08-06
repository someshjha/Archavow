"""S5 export runs

Revision ID: 0006_s5_export
Revises: 0005_s4_review
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_s5_export"
down_revision: Union[str, None] = "0005_s4_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layout", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("includes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("files", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_export_runs_project_id", "export_runs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_export_runs_project_id", table_name="export_runs")
    op.drop_table("export_runs")
