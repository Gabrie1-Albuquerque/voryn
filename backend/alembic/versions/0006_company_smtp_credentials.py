"""add per-tenant SMTP credentials to companies

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-16

Each company can now connect its own SMTP account so appointment
notifications reach clients by email too (previously email only powered
password recovery for the admin panel, never client-facing messages).
smtp_password_encrypted holds a Fernet ciphertext (see core/encryption.py),
not the plaintext password -- the first reversible-encryption secret this
app stores, everything else (refresh tokens, user passwords) is hashed
one-way instead. All columns nullable: no SMTP configured is every
tenant's normal starting state, same as today.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("smtp_host", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("smtp_port", sa.SmallInteger(), nullable=True))
    op.add_column("companies", sa.Column("smtp_username", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("smtp_password_encrypted", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("smtp_from_email", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "smtp_from_email")
    op.drop_column("companies", "smtp_password_encrypted")
    op.drop_column("companies", "smtp_username")
    op.drop_column("companies", "smtp_port")
    op.drop_column("companies", "smtp_host")
