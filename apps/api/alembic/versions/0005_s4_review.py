"""S4 artifacts + review runs + findings

Revision ID: 0005_s4_review
Revises: 0004_s3_knowledge
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_s4_review"
down_revision: Union[str, None] = "0004_s3_knowledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"])

    op.create_table(
        "review_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_review_runs_project_id", "review_runs", ["project_id"])

    op.create_table(
        "review_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "review_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("review_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("line_hint", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_review_findings_review_run_id", "review_findings", ["review_run_id"])


def downgrade() -> None:
    op.drop_index("ix_review_findings_review_run_id", table_name="review_findings")
    op.drop_table("review_findings")
    op.drop_index("ix_review_runs_project_id", table_name="review_runs")
    op.drop_table("review_runs")
    op.drop_index("ix_artifacts_project_id", table_name="artifacts")
    op.drop_table("artifacts")
