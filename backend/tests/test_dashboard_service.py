import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import AppointmentSource, AppointmentStatus
from app.schemas.catalog import ServiceCreateRequest
from app.schemas.client import ClientCreateRequest
from app.schemas.employee import AvailabilityWindow, EmployeeCreateRequest
from app.services import appointment_service, catalog_service, client_service, dashboard_service, employee_service

# A fixed Monday, matching the convention used elsewhere in this suite
# (test_appointments_conflict.py, test_payment_service.py) of pinning a
# known future date rather than using "today" (avoids flakiness from the
# "no past slots" rules elsewhere, and here just keeps the range fixed).
MONDAY = date(2026, 8, 3)
assert MONDAY.weekday() == 0


async def _make_appointment(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    service_id: uuid.UUID,
    employee_id: uuid.UUID,
    starts_at: datetime,
    status: AppointmentStatus,
    is_no_show: bool = False,
):
    client = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Cliente", phone=f"5511{uuid.uuid4().hex[:9]}")
    )
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=client.id,
        employee_id=employee_id,
        service_id=service_id,
        starts_at=starts_at,
        source=AppointmentSource.STAFF,  # starts CONFIRMED, simplest base state to transition from
    )
    if status == AppointmentStatus.COMPLETED:
        appointment = await appointment_service.complete_appointment(
            db_session, tenant_id, appointment.id, changed_by="test"
        )
    elif status == AppointmentStatus.CANCELLED:
        appointment = await appointment_service.cancel_appointment(
            db_session, tenant_id, appointment.id, changed_by="test", is_no_show=is_no_show
        )
    return appointment


@pytest.mark.asyncio
async def test_projected_revenue_excludes_cancelled(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=60, price=Decimal("100.00"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))

    await _make_appointment(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
        status=AppointmentStatus.CONFIRMED,
    )
    await _make_appointment(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        status=AppointmentStatus.CANCELLED,
    )

    summary = await dashboard_service.get_summary(
        db_session, tenant_id, start=date(2026, 8, 1), end=date(2026, 8, 31)
    )

    assert summary.projected_revenue == Decimal("100.00")  # only the still-active one counts


@pytest.mark.asyncio
async def test_realized_revenue_only_counts_completed(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=60, price=Decimal("80.00"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))

    await _make_appointment(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
        status=AppointmentStatus.COMPLETED,
    )
    await _make_appointment(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        status=AppointmentStatus.CONFIRMED,  # not realized yet
    )

    summary = await dashboard_service.get_summary(
        db_session, tenant_id, start=date(2026, 8, 1), end=date(2026, 8, 31)
    )

    assert summary.realized_revenue == Decimal("80.00")


@pytest.mark.asyncio
async def test_no_show_rate_only_counts_completed_and_no_show(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=30, price=Decimal("50"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))

    # 1 completed, 1 no-show, 1 plain cancellation (should NOT count in
    # either bucket -- an advance cancellation isn't a falta).
    await _make_appointment(
        db_session, tenant_id, service_id=service.id, employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc), status=AppointmentStatus.COMPLETED,
    )
    await _make_appointment(
        db_session, tenant_id, service_id=service.id, employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc), status=AppointmentStatus.CANCELLED, is_no_show=True,
    )
    await _make_appointment(
        db_session, tenant_id, service_id=service.id, employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc), status=AppointmentStatus.CANCELLED, is_no_show=False,
    )

    summary = await dashboard_service.get_summary(
        db_session, tenant_id, start=date(2026, 8, 1), end=date(2026, 8, 31)
    )

    assert summary.no_show_rate == pytest.approx(0.5)  # 1 no-show / (1 completed + 1 no-show)


@pytest.mark.asyncio
async def test_no_show_rate_is_none_without_data(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()

    summary = await dashboard_service.get_summary(
        db_session, tenant_id, start=date(2026, 8, 1), end=date(2026, 8, 31)
    )

    assert summary.no_show_rate is None
    assert summary.occupancy_rate is None


@pytest.mark.asyncio
async def test_occupancy_rate_computation(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=240, price=Decimal("100"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))
    await employee_service.replace_employee_availability(
        db_session, tenant_id, employee.id,
        [AvailabilityWindow(weekday=0, start_time=time(9, 0), end_time=time(17, 0))],  # 8h = 480min, only Mondays
    )

    # 4h (240min) booked out of an 8h (480min) Monday window -> 50%.
    await _make_appointment(
        db_session, tenant_id, service_id=service.id, employee_id=employee.id,
        starts_at=datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc), status=AppointmentStatus.CONFIRMED,
    )

    summary = await dashboard_service.get_summary(db_session, tenant_id, start=MONDAY, end=MONDAY + timedelta(days=1))

    assert summary.occupancy_rate == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_top_services_ranking(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    popular = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=30, price=Decimal("50"))
    )
    rare = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Coloração", duration_minutes=90, price=Decimal("200"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))

    for hour in (9, 10, 11):
        await _make_appointment(
            db_session, tenant_id, service_id=popular.id, employee_id=employee.id,
            starts_at=datetime(2026, 8, 3, hour, 0, tzinfo=timezone.utc), status=AppointmentStatus.COMPLETED,
        )
    await _make_appointment(
        db_session, tenant_id, service_id=rare.id, employee_id=employee.id,
        starts_at=datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc), status=AppointmentStatus.COMPLETED,
    )

    summary = await dashboard_service.get_summary(
        db_session, tenant_id, start=date(2026, 8, 1), end=date(2026, 8, 31)
    )

    assert [s.name for s in summary.top_services] == ["Corte", "Coloração"]
    assert summary.top_services[0].completed_count == 3
    assert summary.top_services[0].revenue == Decimal("150.00")


@pytest.mark.asyncio
async def test_start_after_end_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()

    with pytest.raises(ValidationError):
        await dashboard_service.get_summary(db_session, tenant_id, start=date(2026, 8, 10), end=date(2026, 8, 1))
