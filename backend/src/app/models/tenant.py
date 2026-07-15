import uuid
from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.catalog import Service


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant root. Does NOT carry tenant_id itself -- it IS the tenant."""

    __tablename__ = "companies"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    document: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan_tier: Mapped[str] = mapped_column(String(20), default="starter")
    timezone: Mapped[str] = mapped_column(String(50), default="America/Sao_Paulo")
    auto_confirm_public_bookings: Mapped[bool] = mapped_column(Boolean, default=True)
    # Defaults match the hours the reminder worker used before this became
    # configurable (see workers/reminders.py) -- existing tenants keep
    # identical behavior unless they explicitly change these.
    reminder_first_hours: Mapped[int] = mapped_column(SmallInteger, default=24, server_default="24")
    reminder_second_hours: Mapped[int] = mapped_column(SmallInteger, default=2, server_default="2")

    users: Mapped[list["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "reminder_first_hours > reminder_second_hours", name="ck_company_reminder_hours_order"
        ),
        CheckConstraint(
            "reminder_first_hours > 0 AND reminder_second_hours > 0", name="ck_company_reminder_hours_positive"
        ),
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    company: Mapped["Company"] = relationship(back_populates="users")
    employee: Mapped["Employee | None"] = relationship(
        back_populates="user", foreign_keys=[employee_id]
    )


class Employee(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "employees"

    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped["Company"] = relationship(back_populates="employees")
    availability: Mapped[list["EmployeeAvailability"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(
        secondary="employee_service_association", back_populates="employees"
    )
    user: Mapped["User | None"] = relationship(
        back_populates="employee", foreign_keys="User.employee_id", uselist=False
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="employee")


class EmployeeAvailability(UUIDPrimaryKeyMixin, TenantMixin, Base):
    """One row per weekday window an employee can be booked (not a JSON blob, so it stays queryable)."""

    __tablename__ = "employee_availabilities"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 0=Monday .. 6=Sunday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    employee: Mapped["Employee"] = relationship(back_populates="availability")

    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_employee_availability_weekday"),
        CheckConstraint("end_time > start_time", name="ck_employee_availability_time_order"),
    )
