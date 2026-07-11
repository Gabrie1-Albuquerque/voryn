import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import ClientNoteType


class Client(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    notes: Mapped[list["ClientNote"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        order_by="ClientNote.created_at.desc()",
    )

    __table_args__ = (Index("ix_clients_tenant_phone", "tenant_id", "phone"),)


class ClientNote(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """Append-only log: clinical-style records and preference/alert notes share
    this one structure (note_type), never edited/deleted -- only added to,
    matching how real clinical records work and simplifying the audit trail.
    """

    __tablename__ = "client_notes"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    note_type: Mapped[ClientNoteType] = mapped_column(
        pg_enum(ClientNoteType, "client_note_type"), default=ClientNoteType.GENERAL
    )
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="notes")
