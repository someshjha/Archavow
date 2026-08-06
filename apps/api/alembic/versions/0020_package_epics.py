"""Delivery backlog epics + user stories JSON on the package.

Revision ID: 0020_package_epics
Revises: 0019_package_documents
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_package_epics"
down_revision: str | None = "0019_package_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column(
            "epics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "epics")
