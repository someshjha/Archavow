"""Add owner to review_findings

Revision ID: 0011_review_finding_owner
Revises: 0010_package_diagrams
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_review_finding_owner"
down_revision: Union[str, None] = "0010_package_diagrams"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "review_findings",
        sa.Column("owner", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("review_findings", "owner")
