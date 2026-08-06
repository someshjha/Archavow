"""Add ADRs + risks JSON to architecture_packages

Revision ID: 0007_package_adrs_risks
Revises: 0006_s5_export
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_package_adrs_risks"
down_revision: Union[str, None] = "0006_s5_export"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column(
            "adrs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "architecture_packages",
        sa.Column(
            "risks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "risks")
    op.drop_column("architecture_packages", "adrs")
