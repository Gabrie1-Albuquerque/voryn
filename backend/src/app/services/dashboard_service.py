import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import AppointmentStatus
from app.models.tenant import EmployeeAvailability
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import DashboardSummary, TopServiceEntry


def _available_minutes_in_range(
    windows: list[EmployeeAvailability], start: date, end: date
) -> float:
    """EmployeeAvailability is a recurring weekly template (one row per
    employee per weekday window), not a per-day record -- so computing
    capacity for a date range means expanding each matching window across
    every calendar day in [start, end) whose weekday it applies to, not a
    single lookup.
    """
    total_minutes = 0.0
    for offset in range((end - start).days):
        day = start + timedelta(days=offset)
        weekday = day.weekday()
        for window in windows:
            if window.weekday != weekday:
                continue
            start_dt = datetime.combine(day, window.start_time)
            end_dt = datetime.combine(day, window.end_time)
            total_minutes += (end_dt - start_dt).total_seconds() / 60
    return total_minutes


async def get_summary(
    session: AsyncSession, tenant_id: uuid.UUID, *, start: date, end: date
) -> DashboardSummary:
    """start/end are plain calendar dates (start inclusive, end exclusive)
    in the company's own local calendar -- matches EmployeeAvailability's
    weekday windows, which are naive local times with no timezone
    conversion attempted, the same simplification the public booking
    availability calculation makes (this product's whole market is Brazil,
    so cross-timezone drift isn't a real concern worth the complexity).
    """
    if start >= end:
        raise ValidationError("start must be before end")

    repo = DashboardRepository(session, tenant_id)
    range_start = datetime.combine(start, time.min)
    range_end = datetime.combine(end, time.min)

    projected_revenue = await repo.revenue_by_status(
        range_start,
        range_end,
        [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED],
    )
    realized_revenue = await repo.revenue_by_status(range_start, range_end, [AppointmentStatus.COMPLETED])

    completed, no_show = await repo.completed_and_no_show_counts(range_start, range_end)
    no_show_rate = (no_show / (completed + no_show)) if (completed + no_show) > 0 else None

    booked_minutes = await repo.booked_minutes(range_start, range_end)
    windows = await repo.list_active_availability_windows()
    available_minutes = _available_minutes_in_range(windows, start, end)
    occupancy_rate = (booked_minutes / available_minutes) if available_minutes > 0 else None

    top_services = await repo.top_services(range_start, range_end)

    return DashboardSummary(
        period_start=start,
        period_end=end,
        projected_revenue=projected_revenue,
        realized_revenue=realized_revenue,
        no_show_rate=no_show_rate,
        occupancy_rate=occupancy_rate,
        top_services=[
            TopServiceEntry(name=name, completed_count=count, revenue=revenue)
            for name, count, revenue in top_services
        ],
    )
