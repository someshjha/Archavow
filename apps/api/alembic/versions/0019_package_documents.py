"""Package documents JSON (overview, requirements, roadmap, …).

Revision ID: 0019_package_documents
Revises: 0018_option_design
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_package_documents"
down_revision: str | None = "0018_option_design"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "architecture_packages",
        sa.Column(
            "documents",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("architecture_packages", "documents")
