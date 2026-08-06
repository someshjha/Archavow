"""Add mermaid_container to architecture_packages

Revision ID: 0012_package_c4_container
Revises: 0011_review_finding_owner
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_package_c4_container"
down_revision: Union[str, None] = "0011_review_finding_owner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column("mermaid_container", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "mermaid_container")
