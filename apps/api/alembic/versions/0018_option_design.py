"""Option design metadata column (assumptions, constraints, approach).

Revision ID: 0018_option_design
Revises: 0017_seed_source_pgvector
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_option_design"
down_revision: str | None = "0017_seed_source_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "architecture_options",
        sa.Column(
            "design",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("architecture_options", "design")
