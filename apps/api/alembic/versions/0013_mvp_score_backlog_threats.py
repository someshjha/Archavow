"""Add quality_score, backlog, threats to architecture_packages

Revision ID: 0013_mvp_score_backlog_threats
Revises: 0012_package_c4_container
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_mvp_score_backlog_threats"
down_revision: Union[str, None] = "0012_package_c4_container"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column(
            "quality_score",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "architecture_packages",
        sa.Column(
            "backlog",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "architecture_packages",
        sa.Column(
            "threats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "threats")
    op.drop_column("architecture_packages", "backlog")
    op.drop_column("architecture_packages", "quality_score")
