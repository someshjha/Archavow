"""Unique clarification codes + one selected option per project

Revision ID: 0016_concurrency_uniques
Revises: 0015_req_interview_unique
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0016_concurrency_uniques"
down_revision: Union[str, None] = "0015_req_interview_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep exactly one clarification question per (project, code).
    # Prefer answered, then newest created_at, then highest id.
    # (Prior OR-based DELETE could leave mixed-status duplicate pairs.)
    op.execute(
        """
        DELETE FROM clarification_questions q
        WHERE q.id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY project_id, code
                           ORDER BY
                               CASE WHEN status = 'answered' THEN 0 ELSE 1 END,
                               created_at DESC,
                               id DESC
                       ) AS rn
                FROM clarification_questions
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.create_index(
        "uq_clarification_questions_project_code",
        "clarification_questions",
        ["project_id", "code"],
        unique=True,
    )

    # At most one selected option per project — keep newest selected
    op.execute(
        """
        UPDATE architecture_options o
        SET selected = FALSE
        WHERE selected IS TRUE
          AND id NOT IN (
            SELECT DISTINCT ON (project_id) id
            FROM architecture_options
            WHERE selected IS TRUE
            ORDER BY project_id, created_at DESC, id DESC
          )
        """
    )
    op.create_index(
        "uq_architecture_options_one_selected",
        "architecture_options",
        ["project_id"],
        unique=True,
        postgresql_where="selected IS TRUE",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_architecture_options_one_selected",
        table_name="architecture_options",
    )
    op.drop_index(
        "uq_clarification_questions_project_code",
        table_name="clarification_questions",
    )
