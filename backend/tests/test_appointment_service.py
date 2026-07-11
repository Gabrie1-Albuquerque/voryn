"""Service-layer tests for the appointment engine: the state machine and the
application-level conflict pre-check. tests/test_appointments_conflict.py
already covers the DB-level exclusion constraints directly (the actual
concurrency guarantee); this file covers what only exists at the service
layer -- status transitions, the friendly-error path, and reschedule.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.appointment import AppointmentStatusHistory
from app.models.enums import AppointmentSource, AppointmentStatus
from app.schemas.catalog import RoomCreateRequest, ServiceCreateRequest
from app.schemas.client import ClientCreateRequest
from app.schemas.employee import EmployeeCreateRequest
from app.services import appointment_service, catalog_service, client_service, employee_service

BASE_START = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)


async def _seed(db_session: AsyncSession, tenant_id: uuid.UUID, *, requires_room: bool = False) -> dict:
    service = await catalog_service.create_service(
        db_session,
        tenant_id,
        ServiceCreateRequest(name="Corte", duration_minutes=60, price=Decimal("50"), requires_room=requires_room),
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))
    client = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Joana", phone="5511999998888")
    )
    room = None
    if requires_room:
        room = await catalog_service.create_room(db_session, tenant_id, RoomCreateRequest(name="Sala 1"))
    return {"service": service, "employee": employee, "client": client, "room": room}


@pytest.mark.asyncio
async def test_staff_created_appointment_is_confirmed_immediately(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
        source=AppointmentSource.STAFF,
    )

    assert appointment.status == AppointmentStatus.CONFIRMED
    assert appointment.ends_at == BASE_START + timedelta(minutes=60)


@pytest.mark.asyncio
async def test_public_booking_created_appointment_starts_pending(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
        source=AppointmentSource.PUBLIC_BOOKING,
    )

    assert appointment.status == AppointmentStatus.PENDING


@pytest.mark.asyncio
async def test_create_appointment_logs_status_history(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    result = await db_session.execute(
        select(AppointmentStatusHistory).where(AppointmentStatusHistory.appointment_id == appointment.id)
    )
    history = result.scalars().all()
    assert len(history) == 1
    assert history[0].from_status is None
    assert history[0].to_status == AppointmentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_create_appointment_application_level_conflict_check(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    with pytest.raises(ConflictError):
        await appointment_service.create_appointment(
            db_session,
            tenant_id,
            client_id=seed["client"].id,
            employee_id=seed["employee"].id,
            service_id=seed["service"].id,
            starts_at=BASE_START + timedelta(minutes=30),
        )


@pytest.mark.asyncio
async def test_create_appointment_with_unknown_employee_raises_not_found(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    with pytest.raises(NotFoundError):
        await appointment_service.create_appointment(
            db_session,
            tenant_id,
            client_id=seed["client"].id,
            employee_id=uuid.uuid4(),
            service_id=seed["service"].id,
            starts_at=BASE_START,
        )


@pytest.mark.asyncio
async def test_confirm_then_complete_happy_path(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
        source=AppointmentSource.PUBLIC_BOOKING,  # starts Pending, so confirm is meaningful
    )
    assert appointment.status == AppointmentStatus.PENDING

    confirmed = await appointment_service.confirm_appointment(
        db_session, tenant_id, appointment.id, changed_by="staff"
    )
    assert confirmed.status == AppointmentStatus.CONFIRMED

    completed = await appointment_service.complete_appointment(
        db_session, tenant_id, appointment.id, changed_by="staff"
    )
    assert completed.status == AppointmentStatus.COMPLETED


@pytest.mark.asyncio
async def test_cannot_complete_a_pending_appointment(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
        source=AppointmentSource.PUBLIC_BOOKING,
    )

    with pytest.raises(ConflictError):
        await appointment_service.complete_appointment(db_session, tenant_id, appointment.id, changed_by="staff")


@pytest.mark.asyncio
async def test_cannot_transition_out_of_a_terminal_state(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    await appointment_service.cancel_appointment(db_session, tenant_id, appointment.id, changed_by="staff")

    with pytest.raises(ConflictError):
        await appointment_service.confirm_appointment(db_session, tenant_id, appointment.id, changed_by="staff")


@pytest.mark.asyncio
async def test_reschedule_moves_time_and_keeps_status(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    assert appointment.status == AppointmentStatus.CONFIRMED

    new_start = BASE_START + timedelta(days=1)
    rescheduled = await appointment_service.reschedule_appointment(
        db_session, tenant_id, appointment.id, new_starts_at=new_start, changed_by="staff"
    )

    assert rescheduled.starts_at == new_start
    assert rescheduled.status == AppointmentStatus.CONFIRMED  # unchanged, per design


@pytest.mark.asyncio
async def test_reschedule_into_a_conflicting_slot_is_rejected(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    first = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    second_start = BASE_START + timedelta(hours=2)
    second = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=second_start,
    )

    with pytest.raises(ConflictError):
        await appointment_service.reschedule_appointment(
            db_session, tenant_id, second.id, new_starts_at=first.starts_at, changed_by="staff"
        )


@pytest.mark.asyncio
async def test_cannot_reschedule_a_cancelled_appointment(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    await appointment_service.cancel_appointment(db_session, tenant_id, appointment.id, changed_by="staff")

    with pytest.raises(ConflictError):
        await appointment_service.reschedule_appointment(
            db_session, tenant_id, appointment.id, new_starts_at=BASE_START + timedelta(days=1), changed_by="staff"
        )


@pytest.mark.asyncio
async def test_cancelling_an_appointment_frees_the_slot_for_a_new_one(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    await appointment_service.cancel_appointment(db_session, tenant_id, appointment.id, changed_by="staff")

    # Should not raise: a cancelled appointment must not block the same slot.
    new_appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    assert new_appointment.status == AppointmentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_room_conflict_is_enforced_across_different_employees(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id, requires_room=True)
    other_employee = await employee_service.create_employee(
        db_session, tenant_id, EmployeeCreateRequest(name="Outra Funcionaria")
    )

    await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        room_id=seed["room"].id,
        starts_at=BASE_START,
    )

    with pytest.raises(ConflictError):
        await appointment_service.create_appointment(
            db_session,
            tenant_id,
            client_id=seed["client"].id,
            employee_id=other_employee.id,
            service_id=seed["service"].id,
            room_id=seed["room"].id,
            starts_at=BASE_START + timedelta(minutes=15),
        )
