"""Regression tests for a real bug found while building the public booking
flow: set_tenant_context's SET LOCAL is transaction-local, so it reverts the
instant any session.commit() happens. Every service function elsewhere in
this codebase commits exactly once, as the very last thing it does before
its session is discarded, so this never surfaced before -- booking_service's
create_booking/get_booking_status are the first code to chain more than one
committing call (create_appointment, then confirm_appointment or
create_deposit_charge, then get_booking_status's own possible
refresh_payment_status) within a single request/session. Without
re-asserting tenant context after each such commit, the next tenant-scoped
query 500s with "invalid input syntax for type uuid: ''" -- the RLS policy's
own current_setting(...)::uuid cast, evaluated against the reverted value.

These tests use real_tenant/real_session_factory (see conftest.py), not the
ordinary db_session fixture: db_session's session.commit() is secretly a
SAVEPOINT release, not a real commit, so it can never revert a
transaction-local set_config the way a real commit does -- a test built on
it would stay green even if this exact bug came back.
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.models.enums import AppointmentStatus, PaymentStatus
from app.schemas.catalog import ServiceCreateRequest
from app.schemas.employee import AvailabilityWindow, EmployeeCreateRequest
from app.services import booking_service, catalog_service, employee_service
from app.repositories.payment_repository import PaymentRecordRepository

ON_DATE = date(2026, 8, 3)
WEEKDAY = ON_DATE.weekday()


async def _seed(real_session_factory, tenant_id, *, deposit_required: bool):
    async with real_session_factory(tenant_id) as session:
        service = await catalog_service.create_service(
            session,
            tenant_id,
            ServiceCreateRequest(
                name="Corte",
                duration_minutes=60,
                price=Decimal("100.00"),
                deposit_required=deposit_required,
                deposit_type="fixed_amount" if deposit_required else None,
                deposit_value=Decimal("20.00") if deposit_required else None,
            ),
        )
        service_id = service.id

    async with real_session_factory(tenant_id) as session:
        employee = await employee_service.create_employee(
            session, tenant_id, EmployeeCreateRequest(name="Maria", service_ids=[service_id])
        )
        employee_id = employee.id

    async with real_session_factory(tenant_id) as session:
        await employee_service.replace_employee_availability(
            session,
            tenant_id,
            employee_id,
            [AvailabilityWindow(weekday=WEEKDAY, start_time=time(9, 0), end_time=time(12, 0))],
        )

    return service_id, employee_id


@pytest.mark.asyncio
async def test_create_booking_without_deposit_survives_real_commit(real_tenant, real_session_factory):
    tenant_id = real_tenant
    service_id, employee_id = await _seed(real_session_factory, tenant_id, deposit_required=False)

    async with real_session_factory(tenant_id) as session:
        result = await booking_service.create_booking(
            session,
            tenant_id,
            service_id=service_id,
            employee_id=employee_id,
            starts_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
            client_name="Cliente Real",
            client_phone="5511900000001",
            client_email=None,
            notes=None,
            payment_method="pix",
        )

    assert result.status == AppointmentStatus.CONFIRMED

    # A separate follow-up request, exactly like the polling status endpoint.
    async with real_session_factory(tenant_id) as session:
        status = await booking_service.get_booking_status(session, tenant_id, result.id)
    assert status.status == AppointmentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_create_booking_with_deposit_survives_real_commit(real_tenant, real_session_factory):
    tenant_id = real_tenant
    service_id, employee_id = await _seed(real_session_factory, tenant_id, deposit_required=True)

    async with real_session_factory(tenant_id) as session:
        result = await booking_service.create_booking(
            session,
            tenant_id,
            service_id=service_id,
            employee_id=employee_id,
            starts_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
            client_name="Cliente Real Deposito",
            client_phone="5511900000002",
            client_email=None,
            notes=None,
            payment_method="pix",
        )

    assert result.deposit_required is True
    assert result.payment_status == PaymentStatus.APPROVED  # mock provider auto-approves
    assert result.status == AppointmentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_get_booking_status_survives_real_commit_from_pending_refresh(real_tenant, real_session_factory):
    """Forces the payment record back to PENDING after creation (simulating
    a provider that hasn't confirmed yet) so get_booking_status's own
    refresh_payment_status branch -- and the commit it triggers -- actually
    runs, exercising the exact line the fix in get_booking_status protects.
    """
    tenant_id = real_tenant
    service_id, employee_id = await _seed(real_session_factory, tenant_id, deposit_required=True)

    async with real_session_factory(tenant_id) as session:
        created = await booking_service.create_booking(
            session,
            tenant_id,
            service_id=service_id,
            employee_id=employee_id,
            starts_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
            client_name="Cliente Pendente",
            client_phone="5511900000003",
            client_email=None,
            notes=None,
            payment_method="pix",
        )

    async with real_session_factory(tenant_id) as session:
        records = await PaymentRecordRepository(session, tenant_id).list(appointment_id=created.id)
        record = records[0]
        record.status = PaymentStatus.PENDING
        await session.commit()

    async with real_session_factory(tenant_id) as session:
        status = await booking_service.get_booking_status(session, tenant_id, created.id)

    # Mock provider's get_charge_status always reports "approved", so the
    # forced-PENDING record should flip back once refreshed.
    assert status.payment_status == PaymentStatus.APPROVED
    assert status.status == AppointmentStatus.CONFIRMED
