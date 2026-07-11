"""add is_no_show flag to appointments

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-11

A no-show is modeled as a CANCELLED appointment with this flag set, not a
new terminal status -- CANCELLED already has the correct side effects
everywhere (excluded from the exclusion constraints, from has_conflict(),
frees the slot, triggers waitlist promotion); a new status would need every
one of those taught about it too. This flag exists so the dashboard's
"taxa de faltas" (Milestone 10) has a real signal instead of an inference
over timing -- the original spec names it as the product's headline metric.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "appointments", sa.Column("is_no_show", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )


def downgrade() -> None:
    op.drop_column("appointments", "is_no_show")
