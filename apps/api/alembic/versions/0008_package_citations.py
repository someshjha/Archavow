"""Add citations + retrieval_status to architecture_packages

Revision ID: 0008_package_citations
Revises: 0007_package_adrs_risks
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_package_citations"
down_revision: Union[str, None] = "0007_package_adrs_risks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "architecture_packages",
        sa.Column(
            "retrieval_status",
            sa.String(length=32),
            nullable=False,
            server_default="ok",
        ),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "retrieval_status")
    op.drop_column("architecture_packages", "citations")
