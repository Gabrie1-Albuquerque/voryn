import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.appointment import Appointment, AppointmentStatusHistory
from app.models.catalog import Service
from app.models.enums import AppointmentSource, AppointmentStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.catalog_repository import RoomRepository, ServiceRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.employee_repository import EmployeeRepository

# Explicit allowed-transitions map: any transition not listed here is
# rejected, so status can never move via an arbitrary router-level write --
# only through the functions below, each of which goes through _transition.
# RESCHEDULED is a valid enum value (matches the original spec's literal
# status list, and is already a Postgres enum member as of migration 0001)
# but is deliberately not part of this graph: rescheduling (see
# reschedule_appointment) is modeled as a time change on the existing
# Pending/Confirmed row, not a distinct resting state -- a calendar
# shouldn't show an appointment mysteriously parked in "Rescheduled" instead
# of its actual confirmation state at the new time.
_ALLOWED_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.PENDING: {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CONFIRMED: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED},
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.COMPLETED: set(),
}


async def has_conflict(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    employee_id: uuid.UUID,
    room_id: uuid.UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    exclude_appointment_id: uuid.UUID | None = None,
) -> bool:
    """Application-level pre-check: a fast, friendly-error nicety on top of
    the DB exclusion constraints (see migration 0001), which remain the
    actual source of truth under concurrency -- this alone would be a race
    condition once the public booking page (milestone 9) lets a staff
    member and a customer fight over the same slot. Also the one function
    milestone 9's availability computation reuses (inverted: iterate
    candidate slots, keep the ones this returns False for), so display and
    write-time validation can never drift apart.
    """
    base_conditions = [
        Appointment.tenant_id == tenant_id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
    ]
    if exclude_appointment_id is not None:
        base_conditions.append(Appointment.id != exclude_appointment_id)

    employee_stmt = select(Appointment.id).where(*base_conditions, Appointment.employee_id == employee_id).limit(1)
    if (await session.execute(employee_stmt)).first() is not None:
        return True

    if room_id is not None:
        room_stmt = select(Appointment.id).where(*base_conditions, Appointment.room_id == room_id).limit(1)
        if (await session.execute(room_stmt)).first() is not None:
            return True

    return False


async def _load_service(session: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Service:
    service = await ServiceRepository(session, tenant_id).get(service_id)
    if service is None:
        raise NotFoundError("service not found")
    return service


async def list_appointments(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start: datetime,
    end: datetime,
    employee_id: uuid.UUID | None = None,
) -> list[Appointment]:
    return await AppointmentRepository(session, tenant_id).list_in_range(start, end, employee_id=employee_id)


async def get_appointment(session: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
    appointment = await AppointmentRepository(session, tenant_id).get_with_relations(appointment_id)
    if appointment is None:
        raise NotFoundError("appointment not found")
    return appointment


async def create_appointment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    service_id: uuid.UUID,
    starts_at: datetime,
    room_id: uuid.UUID | None = None,
    source: AppointmentSource = AppointmentSource.STAFF,
    created_by_user_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> Appointment:
    service = await _load_service(session, tenant_id, service_id)
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    effective_room_id = room_id if service.requires_room else None

    # Checked explicitly (rather than left to surface as a foreign key
    # IntegrityError) so a bad id is a clear 404, not lumped in with the
    # exclusion-constraint IntegrityError this function also catches below
    # for the scheduling-conflict case -- those two failure modes need to
    # stay distinguishable.
    if await ClientRepository(session, tenant_id).get(client_id) is None:
        raise NotFoundError("client not found")
    if await EmployeeRepository(session, tenant_id).get(employee_id) is None:
        raise NotFoundError("employee not found")
    if effective_room_id is not None and await RoomRepository(session, tenant_id).get(effective_room_id) is None:
        raise NotFoundError("room not found")

    if await has_conflict(
        session, tenant_id, employee_id=employee_id, room_id=effective_room_id, starts_at=starts_at, ends_at=ends_at
    ):
        raise ConflictError("Este horário não está mais disponível")

    # Staff creating an appointment IS the confirmation (no separate
    # "confirm your own booking" step); public bookings (milestone 9) start
    # Pending and are confirmed either automatically or by a deposit
    # clearing, per Company.auto_confirm_public_bookings.
    initial_status = AppointmentStatus.CONFIRMED if source == AppointmentSource.STAFF else AppointmentStatus.PENDING

    appointment = AppointmentRepository(session, tenant_id).add(
        Appointment(
            client_id=client_id,
            employee_id=employee_id,
            service_id=service_id,
            room_id=effective_room_id,
            starts_at=starts_at,
            ends_at=ends_at,
            status=initial_status,
            source=source,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )
    )
    session.add(
        AppointmentStatusHistory(
            tenant_id=tenant_id,
            appointment=appointment,
            from_status=None,
            to_status=initial_status,
            changed_by=str(created_by_user_id) if created_by_user_id else source.value,
        )
    )
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Este horário não está mais disponível") from exc

    result = await get_appointment(session, tenant_id, appointment.id)
    await session.commit()
    return result


async def _transition(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    appointment: Appointment,
    to_status: AppointmentStatus,
    *,
    changed_by: str,
) -> Appointment:
    allowed = _ALLOWED_TRANSITIONS.get(appointment.status, set())
    if to_status not in allowed:
        raise ConflictError(
            f"cannot move an appointment from {appointment.status.value!r} to {to_status.value!r}"
        )
    from_status = appointment.status
    appointment.status = to_status
    session.add(
        AppointmentStatusHistory(
            tenant_id=tenant_id,
            appointment_id=appointment.id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
        )
    )
    await session.flush()
    result = await get_appointment(session, tenant_id, appointment.id)
    await session.commit()
    return result


async def confirm_appointment(
    session: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID, *, changed_by: str
) -> Appointment:
    appointment = await get_appointment(session, tenant_id, appointment_id)
    return await _transition(session, tenant_id, appointment, AppointmentStatus.CONFIRMED, changed_by=changed_by)


async def complete_appointment(
    session: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID, *, changed_by: str
) -> Appointment:
    appointment = await get_appointment(session, tenant_id, appointment_id)
    return await _transition(session, tenant_id, appointment, AppointmentStatus.COMPLETED, changed_by=changed_by)


async def cancel_appointment(
    session: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID, *, changed_by: str
) -> Appointment:
    appointment = await get_appointment(session, tenant_id, appointment_id)
    result = await _transition(session, tenant_id, appointment, AppointmentStatus.CANCELLED, changed_by=changed_by)
    # Automações (milestone 7) hooks waitlist promotion in here: the moment
    # a slot frees up is exactly this transition, and it's lower-latency to
    # check here than to wait for a periodic scan.
    return result


async def reschedule_appointment(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    appointment_id: uuid.UUID,
    *,
    new_starts_at: datetime,
    changed_by: str,
) -> Appointment:
    """Moves the same row to a new time (what drag-and-drop in the agenda
    does) rather than creating a new appointment and marking this one
    RESCHEDULED -- see the module docstring on _ALLOWED_TRANSITIONS for why
    that enum value isn't used as a resting state. Confirmation status is
    left untouched: dragging a confirmed appointment to a new slot doesn't
    un-confirm it.
    """
    appointment = await get_appointment(session, tenant_id, appointment_id)
    if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        raise ConflictError(f"cannot reschedule a {appointment.status.value} appointment")

    service = await _load_service(session, tenant_id, appointment.service_id)
    new_ends_at = new_starts_at + timedelta(minutes=service.duration_minutes)

    if await has_conflict(
        session,
        tenant_id,
        employee_id=appointment.employee_id,
        room_id=appointment.room_id,
        starts_at=new_starts_at,
        ends_at=new_ends_at,
        exclude_appointment_id=appointment.id,
    ):
        raise ConflictError("Este horário não está mais disponível")

    appointment.starts_at = new_starts_at
    appointment.ends_at = new_ends_at
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Este horário não está mais disponível") from exc

    result = await get_appointment(session, tenant_id, appointment.id)
    await session.commit()
    return result
