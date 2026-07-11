import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType


class NotificationLog(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """Record of every notification attempt. Also what reminder-scan idempotency
    checks against before enqueueing (see workers/reminders.py): a
    (appointment_id, notification_type) pair already logged as sent/queued means
    skip, so the periodic scan can run at any frequency without double-sending.
    """

    __tablename__ = "notification_logs"

    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel")
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        pg_enum(NotificationType, "notification_type")
    )
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus, "notification_status"), default=NotificationStatus.QUEUED
    )
    provider_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_notification_logs_idempotency",
            "tenant_id",
            "appointment_id",
            "notification_type",
        ),
    )
