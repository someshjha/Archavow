"""Add sequence + deploy mermaid columns

Revision ID: 0010_package_diagrams
Revises: 0009_package_ai_summary
Create Date: 2026-07-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_package_diagrams"
down_revision: Union[str, None] = "0009_package_ai_summary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column("mermaid_sequence", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "architecture_packages",
        sa.Column("mermaid_deploy", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "mermaid_deploy")
    op.drop_column("architecture_packages", "mermaid_sequence")
