import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import AppointmentStatus, PaymentStatus
from app.schemas.catalog import ServiceCreateRequest
from app.schemas.employee import AvailabilityWindow, EmployeeCreateRequest
from app.services import booking_service, catalog_service, employee_service

# A fixed future date; the test derives its own weekday from it rather than
# assuming which day of the week this happens to be, so it stays correct
# even if this constant is ever changed.
ON_DATE = date(2026, 8, 3)
WEEKDAY = ON_DATE.weekday()


async def _seed_bookable(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    deposit_required: bool = False,
    requires_room: bool = False,
):
    service = await catalog_service.create_service(
        db_session,
        tenant_id,
        ServiceCreateRequest(
            name="Corte",
            duration_minutes=60,
            price=Decimal("100.00"),
            requires_room=requires_room,
            deposit_required=deposit_required,
            deposit_type="fixed_amount" if deposit_required else None,
            deposit_value=Decimal("20.00") if deposit_required else None,
        ),
    )
    employee = await employee_service.create_employee(
        db_session, tenant_id, EmployeeCreateRequest(name="Maria", service_ids=[service.id])
    )
    await employee_service.replace_employee_availability(
        db_session,
        tenant_id,
        employee.id,
        [AvailabilityWindow(weekday=WEEKDAY, start_time=time(9, 0), end_time=time(12, 0))],
    )
    return service, employee


@pytest.mark.asyncio
async def test_list_bookable_services_excludes_inactive(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    active = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=30, price=Decimal("50"))
    )
    inactive = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Escova", duration_minutes=30, price=Decimal("40"))
    )
    await catalog_service.deactivate_service(db_session, tenant_id, inactive.id)

    services = await booking_service.list_bookable_services(db_session, tenant_id)

    assert [s.id for s in services] == [active.id]


@pytest.mark.asyncio
async def test_list_active_employees_excludes_inactive(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    active = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))
    inactive = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Joana"))
    await employee_service.deactivate_employee(db_session, tenant_id, inactive.id)

    employees = await booking_service.list_active_employees(db_session, tenant_id)

    assert [e.id for e in employees] == [active.id]


@pytest.mark.asyncio
async def test_availability_respects_employee_window(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)

    slots = await booking_service.compute_availability(
        db_session, tenant_id, employee_id=employee.id, service_id=service.id, on_date=ON_DATE
    )

    # 09:00-12:00 window, 60min service, 15min step -> last bookable start is 11:00.
    assert len(slots) == 9
    first_local = slots[0].astimezone(ZoneInfo("America/Sao_Paulo"))
    assert (first_local.hour, first_local.minute) == (9, 0)


@pytest.mark.asyncio
async def test_availability_excludes_already_booked_slot(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)

    starts_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)  # 09:00 in America/Sao_Paulo (UTC-3)
    result = await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=starts_at,
        client_name="Joana",
        client_phone="5511999998888",
        client_email=None,
        notes=None,
        payment_method="pix",
    )
    assert result.status == AppointmentStatus.CONFIRMED

    slots = await booking_service.compute_availability(
        db_session, tenant_id, employee_id=employee.id, service_id=service.id, on_date=ON_DATE
    )

    assert starts_at not in slots


@pytest.mark.asyncio
async def test_availability_unknown_employee_service_pair_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)
    other_service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Barba", duration_minutes=30, price=Decimal("30"))
    )

    with pytest.raises(NotFoundError):
        await booking_service.compute_availability(
            db_session, tenant_id, employee_id=employee.id, service_id=other_service.id, on_date=ON_DATE
        )


@pytest.mark.asyncio
async def test_create_booking_without_deposit_auto_confirms(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)
    starts_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)  # 09:00 in America/Sao_Paulo (UTC-3)

    result = await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=starts_at,
        client_name="Joana",
        client_phone="5511999998888",
        client_email="joana@example.com",
        notes="Primeira vez",
        payment_method="pix",
    )

    assert result.status == AppointmentStatus.CONFIRMED
    assert result.deposit_required is False
    assert result.payment_status is None


@pytest.mark.asyncio
async def test_create_booking_with_deposit_stays_pending_until_approved(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id, deposit_required=True)
    starts_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    result = await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=starts_at,
        client_name="Joana",
        client_phone="5511999998888",
        client_email=None,
        notes=None,
        payment_method="pix",
    )

    # Mock provider auto-approves, so this should already be confirmed --
    # the important thing is that it *went through* PaymentRecord creation
    # (payment_status/deposit_amount populated), not that it stayed pending.
    assert result.deposit_required is True
    assert result.deposit_amount == Decimal("20.00")
    assert result.payment_status == PaymentStatus.APPROVED
    assert result.status == AppointmentStatus.CONFIRMED
    assert result.pix_qr_code is not None


@pytest.mark.asyncio
async def test_create_booking_reuses_existing_client_by_phone(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)
    starts_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    other_starts_at = starts_at + timedelta(hours=1)

    first = await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=starts_at,
        client_name="Joana",
        client_phone="5511999998888",
        client_email=None,
        notes=None,
        payment_method="pix",
    )
    second = await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=other_starts_at,
        client_name="Joana Souza",  # same phone, different name typed in
        client_phone="5511999998888",
        client_email=None,
        notes=None,
        payment_method="pix",
    )

    assert first.id != second.id
    from app.repositories.client_repository import ClientRepository

    clients = await ClientRepository(db_session, tenant_id).list(phone="5511999998888")
    assert len(clients) == 1
    assert clients[0].name == "Joana"  # first booking's name wins, not overwritten


@pytest.mark.asyncio
async def test_create_booking_conflict_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)
    starts_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=starts_at,
        client_name="Joana",
        client_phone="5511999998888",
        client_email=None,
        notes=None,
        payment_method="pix",
    )

    with pytest.raises(ConflictError):
        await booking_service.create_booking(
            db_session,
            tenant_id,
            service_id=service.id,
            employee_id=employee.id,
            starts_at=starts_at,
            client_name="Outra Cliente",
            client_phone="5511999997777",
            client_email=None,
            notes=None,
            payment_method="pix",
        )


@pytest.mark.asyncio
async def test_get_booking_status_matches_created_booking(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    service, employee = await _seed_bookable(db_session, tenant_id)
    starts_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    created = await booking_service.create_booking(
        db_session,
        tenant_id,
        service_id=service.id,
        employee_id=employee.id,
        starts_at=starts_at,
        client_name="Joana",
        client_phone="5511999998888",
        client_email=None,
        notes=None,
        payment_method="pix",
    )

    fetched = await booking_service.get_booking_status(db_session, tenant_id, created.id)

    assert fetched.id == created.id
    assert fetched.status == created.status
    assert fetched.starts_at == created.starts_at
