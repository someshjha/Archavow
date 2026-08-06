"""S1 intake columns + requirements + clarification_questions

Revision ID: 0002_s1_requirements
Revises: 0001_initial
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_s1_requirements"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("business_objective", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("problem_statement", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("preferred_cloud", sa.String(length=64), nullable=True))
    op.add_column("projects", sa.Column("scale_availability", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("tech_constraints", sa.Text(), nullable=True))

    op.create_table(
        "requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_requirements_project_id", "requirements", ["project_id"])

    op.create_table(
        "clarification_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_clarification_questions_project_id", "clarification_questions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_clarification_questions_project_id", table_name="clarification_questions")
    op.drop_table("clarification_questions")
    op.drop_index("ix_requirements_project_id", table_name="requirements")
    op.drop_table("requirements")
    op.drop_column("projects", "tech_constraints")
    op.drop_column("projects", "scale_availability")
    op.drop_column("projects", "preferred_cloud")
    op.drop_column("projects", "problem_statement")
    op.drop_column("projects", "business_objective")
