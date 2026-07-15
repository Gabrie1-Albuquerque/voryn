"""add configurable reminder hours to companies

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-15

Reminder timing (workers/reminders.py) was hardcoded to 24h/2h before an
appointment for every tenant. These two columns let each company pick its
own offsets from the settings screen; server_default matches the old
hardcoded values so existing tenants see no behavior change until they
explicitly configure something different.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("reminder_first_hours", sa.SmallInteger(), nullable=False, server_default="24"),
    )
    op.add_column(
        "companies",
        sa.Column("reminder_second_hours", sa.SmallInteger(), nullable=False, server_default="2"),
    )
    op.create_check_constraint(
        "ck_company_reminder_hours_order", "companies", "reminder_first_hours > reminder_second_hours"
    )
    op.create_check_constraint(
        "ck_company_reminder_hours_positive",
        "companies",
        "reminder_first_hours > 0 AND reminder_second_hours > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_company_reminder_hours_positive", "companies", type_="check")
    op.drop_constraint("ck_company_reminder_hours_order", "companies", type_="check")
    op.drop_column("companies", "reminder_second_hours")
    op.drop_column("companies", "reminder_first_hours")
