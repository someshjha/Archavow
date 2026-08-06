"""S2 architecture_options + packages

Revision ID: 0003_s2_options
Revises: 0002_s1_requirements
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_s2_options"
down_revision: Union[str, None] = "0002_s1_requirements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "architecture_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("pros", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fit_score", sa.Integer(), nullable=False),
        sa.Column("cost_band", sa.String(length=16), nullable=False),
        sa.Column("ops_band", sa.String(length=32), nullable=False),
        sa.Column("recommended", sa.Boolean(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("stack", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_architecture_options_project_id", "architecture_options", ["project_id"])

    op.create_table(
        "architecture_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "option_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("architecture_options.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("hld_markdown", sa.Text(), nullable=False),
        sa.Column("mermaid", sa.Text(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_architecture_packages_project_id", "architecture_packages", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_architecture_packages_project_id", table_name="architecture_packages")
    op.drop_table("architecture_packages")
    op.drop_index("ix_architecture_options_project_id", table_name="architecture_options")
    op.drop_table("architecture_options")
