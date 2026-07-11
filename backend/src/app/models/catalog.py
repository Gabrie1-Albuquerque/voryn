from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import DepositType

if TYPE_CHECKING:
    from app.models.tenant import Employee

employee_service_association = Table(
    "employee_service_association",
    Base.metadata,
    Column("employee_id", UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Service(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Catalog item ("Serviços"). Deposit fields (addition #2) are embedded
    directly rather than a child table since they're always 0-or-1 per service.
    """

    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(200))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    requires_room: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    deposit_required: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_type: Mapped[DepositType | None] = mapped_column(
        pg_enum(DepositType, "deposit_type"), nullable=True
    )
    deposit_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    employees: Mapped[list["Employee"]] = relationship(
        secondary=employee_service_association, back_populates="services"
    )


class Room(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Generic exclusive-use resource: a physical room, a chair, any bookable resource."""

    __tablename__ = "rooms"

    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
