"""Add origin column to architecture_options

Revision ID: 0014_option_origin
Revises: 0013_mvp_score_backlog_threats
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_option_origin"
down_revision: Union[str, None] = "0013_mvp_score_backlog_threats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_options",
        sa.Column(
            "origin",
            sa.String(length=16),
            nullable=False,
            server_default="template",
        ),
    )
    # Recover AI-scored options persisted before this column existed.
    # Starter templates always carry the explicit summary prefix.
    op.execute(
        sa.text(
            "UPDATE architecture_options SET origin = 'ai' "
            "WHERE summary NOT LIKE '[Starter template]%'"
        )
    )


def downgrade() -> None:
    op.drop_column("architecture_options", "origin")
