import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.catalog import Service
from app.models.enums import AppointmentStatus
from app.models.tenant import Employee, EmployeeAvailability


class DashboardRepository:
    """Aggregation queries backing the management dashboard (Milestone 10).
    Kept separate from the CRUD repositories in this module (which are all
    TenantScopedRepository[SingleModel]) since these span multiple tables
    and never map to a single ORM entity -- there's no single "Dashboard"
    model to scope generically the way TenantScopedRepository does.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def revenue_by_status(
        self, start: datetime, end: datetime, statuses: list[AppointmentStatus]
    ) -> Decimal:
        """Revenue is the service's full ticket price, not the deposit
        amount on file -- a deposit is a partial pre-payment mechanism to
        deter no-shows, not a separate revenue figure to report.
        """
        stmt = (
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Appointment)
            .join(Service, Service.id == Appointment.service_id)
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.starts_at >= start,
                Appointment.starts_at < end,
                Appointment.status.in_(statuses),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def completed_and_no_show_counts(self, start: datetime, end: datetime) -> tuple[int, int]:
        stmt = (
            select(Appointment.status, Appointment.is_no_show, func.count())
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.starts_at >= start,
                Appointment.starts_at < end,
                Appointment.status.in_([AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]),
            )
            .group_by(Appointment.status, Appointment.is_no_show)
        )
        result = await self.session.execute(stmt)
        completed = 0
        no_show = 0
        for status, is_no_show, count in result.all():
            if status == AppointmentStatus.COMPLETED:
                completed += count
            elif status == AppointmentStatus.CANCELLED and is_no_show:
                no_show += count
        return completed, no_show

    async def booked_minutes(self, start: datetime, end: datetime) -> float:
        stmt = select(
            func.coalesce(func.sum(func.extract("epoch", Appointment.ends_at - Appointment.starts_at)), 0)
        ).where(
            Appointment.tenant_id == self.tenant_id,
            Appointment.starts_at >= start,
            Appointment.starts_at < end,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        result = await self.session.execute(stmt)
        return float(result.scalar_one()) / 60

    async def list_active_availability_windows(self) -> list[EmployeeAvailability]:
        """Not date-ranged: EmployeeAvailability is a recurring weekly
        template, not a per-day record -- expanding it across the requested
        period is dashboard_service's job (get_summary), not this query's.
        """
        stmt = (
            select(EmployeeAvailability)
            .join(Employee, Employee.id == EmployeeAvailability.employee_id)
            .where(EmployeeAvailability.tenant_id == self.tenant_id, Employee.is_active.is_(True))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def top_services(
        self, start: datetime, end: datetime, limit: int = 10
    ) -> list[tuple[str, int, Decimal]]:
        stmt = (
            select(Service.name, func.count(Appointment.id), func.coalesce(func.sum(Service.price), 0))
            .select_from(Appointment)
            .join(Service, Service.id == Appointment.service_id)
            .where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.starts_at >= start,
                Appointment.starts_at < end,
                Appointment.status == AppointmentStatus.COMPLETED,
            )
            .group_by(Service.id, Service.name)
            .order_by(func.count(Appointment.id).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.all())
