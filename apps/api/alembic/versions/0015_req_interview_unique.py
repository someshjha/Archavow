"""Unique interview requirement source per project + dedupe

Revision ID: 0015_req_interview_unique
Revises: 0014_option_origin
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0015_req_interview_unique"
down_revision: Union[str, None] = "0014_option_origin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the newest row when concurrent answers created duplicates.
    # Delete older duplicates (smaller created_at), not the newest.
    op.execute(
        """
        DELETE FROM requirements older
        USING requirements newer
        WHERE older.source LIKE 'interview:%'
          AND newer.source = older.source
          AND newer.project_id = older.project_id
          AND older.created_at < newer.created_at
        """
    )
    # Same timestamp: keep the higher id
    op.execute(
        """
        DELETE FROM requirements loser
        USING requirements keeper
        WHERE loser.source LIKE 'interview:%'
          AND keeper.source = loser.source
          AND keeper.project_id = loser.project_id
          AND keeper.created_at = loser.created_at
          AND loser.id < keeper.id
        """
    )
    op.create_index(
        "uq_requirements_project_interview_source",
        "requirements",
        ["project_id", "source"],
        unique=True,
        postgresql_where="source LIKE 'interview:%'",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_requirements_project_interview_source",
        table_name="requirements",
    )
