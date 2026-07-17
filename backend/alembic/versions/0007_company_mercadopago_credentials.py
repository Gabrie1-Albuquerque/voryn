"""add per-tenant Mercado Pago credentials to companies

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-17

Deposit (sinal) charges were built on a single global MERCADOPAGO_ACCESS_TOKEN,
which would route every tenant's client payments into the platform owner's
account. These columns let each company connect its own Mercado Pago account
(production APP_USR- token), so deposits land directly with the business.
Fernet ciphertexts (core/encryption.py), same pattern as the SMTP columns
from migration 0006. Nullable: not configured is every tenant's normal
starting state -- payment_service falls back to the global (mock) provider.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("mp_access_token_encrypted", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("mp_webhook_secret_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "mp_webhook_secret_encrypted")
    op.drop_column("companies", "mp_access_token_encrypted")
