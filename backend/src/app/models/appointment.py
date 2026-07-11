import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import AppointmentSource, AppointmentStatus, WaitlistStatus

if TYPE_CHECKING:
    from app.models.catalog import Room, Service
    from app.models.client import Client
    from app.models.payment import PaymentRecord
    from app.models.tenant import Employee


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "appointments"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), index=True
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    # Denormalized from starts_at + service.duration_minutes at creation time so
    # conflict queries never need a join just to know an appointment's end.
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    status: Mapped[AppointmentStatus] = mapped_column(
        pg_enum(AppointmentStatus, "appointment_status"),
        default=AppointmentStatus.PENDING,
        index=True,
    )
    source: Mapped[AppointmentSource] = mapped_column(
        pg_enum(AppointmentSource, "appointment_source"), default=AppointmentSource.STAFF
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    client: Mapped["Client"] = relationship()
    employee: Mapped["Employee"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship()
    room: Mapped["Room | None"] = relationship()
    status_history: Mapped[list["AppointmentStatusHistory"]] = relationship(
        back_populates="appointment",
        cascade="all, delete-orphan",
        order_by="AppointmentStatusHistory.changed_at",
    )
    payments: Mapped[list["PaymentRecord"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_appointments_tenant_employee_starts", "tenant_id", "employee_id", "starts_at"),
        Index("ix_appointments_tenant_room_starts", "tenant_id", "room_id", "starts_at"),
        Index("ix_appointments_tenant_status", "tenant_id", "status"),
        # Application-layer conflict checks (appointment_service.py) are backed by
        # these DB-level exclusion constraints -- the actual source of truth under
        # concurrency (e.g. a staff member and a public-booking customer racing for
        # the same slot). Requires `CREATE EXTENSION btree_gist`, added in the first
        # migration. See that migration for the authoritative DDL; these ORM-level
        # declarations exist for documentation and metadata.create_all() consistency.
        ExcludeConstraint(
            ("tenant_id", "="),
            ("employee_id", "="),
            (text("tstzrange(starts_at, ends_at)"), "&&"),
            where=text("status <> 'cancelled'"),
            using="gist",
            name="excl_appointments_employee_overlap",
        ),
        ExcludeConstraint(
            ("tenant_id", "="),
            ("room_id", "="),
            (text("tstzrange(starts_at, ends_at)"), "&&"),
            where=text("status <> 'cancelled' AND room_id IS NOT NULL"),
            using="gist",
            name="excl_appointments_room_overlap",
        ),
    )


class AppointmentStatusHistory(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """Satisfies the spec's Auditoria requirement for the single most important
    trail in the system: who changed what appointment's status, and when.
    """

    __tablename__ = "appointment_status_history"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[AppointmentStatus | None] = mapped_column(
        pg_enum(AppointmentStatus, "appointment_status"), nullable=True
    )
    to_status: Mapped[AppointmentStatus] = mapped_column(pg_enum(AppointmentStatus, "appointment_status"))
    # Free-form actor identifier: a user UUID as text, or "system" / "client_whatsapp" / "public_booking".
    changed_by: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    appointment: Mapped["Appointment"] = relationship(back_populates="status_history")


class WaitlistEntry(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "waitlist_entries"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), index=True
    )
    preferred_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    preferred_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    preferred_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[WaitlistStatus] = mapped_column(
        pg_enum(WaitlistStatus, "waitlist_status"), default=WaitlistStatus.WAITING, index=True
    )
