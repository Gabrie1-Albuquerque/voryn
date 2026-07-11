"""persist pix_qr_code/checkout_url on payment_records

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-11

Originally these were deliberately left transient (only ever in-memory, on
the response of the create-charge call) -- see payment_service.py's
DepositChargeResult docstring. Building the public booking page (milestone 9)
surfaced why that doesn't hold for an unauthenticated client on their own
device: reloading the booking-status tab mid-PIX-payment is normal usage,
not a rare edge case, and Mercado Pago's status-refresh endpoint doesn't
re-return the QR payload -- so it must be captured once at charge creation
or it's unrecoverable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payment_records", sa.Column("pix_qr_code", sa.Text(), nullable=True))
    op.add_column("payment_records", sa.Column("checkout_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_records", "checkout_url")
    op.drop_column("payment_records", "pix_qr_code")
