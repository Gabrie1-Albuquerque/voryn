import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import PaymentMethod, PaymentProviderName, PaymentStatus, PaymentType

if TYPE_CHECKING:
    from app.models.appointment import Appointment


class PaymentRecord(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "payment_records"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[PaymentProviderName] = mapped_column(
        pg_enum(PaymentProviderName, "payment_provider_name")
    )
    provider_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    type: Mapped[PaymentType] = mapped_column(pg_enum(PaymentType, "payment_type"))
    method: Mapped[PaymentMethod] = mapped_column(pg_enum(PaymentMethod, "payment_method"))
    status: Mapped[PaymentStatus] = mapped_column(
        pg_enum(PaymentStatus, "payment_status"), default=PaymentStatus.PENDING, index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Persisted despite being provider-response data, not app state: the first
    # consumer of a PENDING PIX charge is now the public booking page (an
    # unauthenticated client on their own device), where losing the tab or
    # reloading mid-payment is normal PIX usage, not an edge case -- unlike
    # the staff-facing deposit screen this was originally written for, which
    # stays on one continuous screen. Mercado Pago's own status-refresh
    # endpoint doesn't re-return this, so it must be captured once at charge
    # creation or it's gone forever.
    pix_qr_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    appointment: Mapped["Appointment"] = relationship(back_populates="payments")
