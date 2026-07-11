import uuid
from datetime import date as date_
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_tenant_context
from app.core.exceptions import ConflictError, NotFoundError
from app.models.catalog import Service
from app.models.client import Client
from app.models.enums import AppointmentSource, PaymentStatus
from app.models.tenant import Company, Employee
from app.providers.payments.base import PaymentMethodLiteral
from app.repositories.catalog_repository import RoomRepository, ServiceRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.payment_repository import PaymentRecordRepository
from app.schemas.public_booking import PublicBookingResponse
from app.services import appointment_service, payment_service

# Fixed granularity for the public slot picker, independent of each
# service's own duration -- lets services of different lengths share one
# time grid instead of each drawing its own, matching how every competitor
# booking page (Booksy, Fresha, Calendly) presents availability.
_SLOT_STEP_MINUTES = 15


async def get_company(session: AsyncSession, tenant_id: uuid.UUID) -> Company:
    # Company.id IS the tenant id (see models/tenant.py) -- a plain get() by
    # primary key, not a repository: companies has no RLS policy and no
    # tenant_id column of its own, it IS the tenant root.
    company = await session.get(Company, tenant_id)
    if company is None:
        raise NotFoundError("company not found")
    return company


async def list_bookable_services(session: AsyncSession, tenant_id: uuid.UUID) -> list[Service]:
    return await ServiceRepository(session, tenant_id).list(is_active=True)


async def list_active_employees(session: AsyncSession, tenant_id: uuid.UUID) -> list[Employee]:
    employees = await EmployeeRepository(session, tenant_id).list_with_relations()
    return [e for e in employees if e.is_active]


async def _get_bookable_service(session: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Service:
    service = await ServiceRepository(session, tenant_id).get(service_id)
    if service is None or not service.is_active:
        raise NotFoundError("service not found")
    return service


async def _get_qualified_employee(
    session: AsyncSession, tenant_id: uuid.UUID, employee_id: uuid.UUID, service_id: uuid.UUID
) -> Employee:
    employee = await EmployeeRepository(session, tenant_id).get_with_relations(employee_id)
    if employee is None or not employee.is_active or not any(s.id == service_id for s in employee.services):
        raise NotFoundError("employee not found or does not offer this service")
    return employee


async def _has_capacity(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    employee_id: uuid.UUID,
    service: Service,
    starts_at: datetime,
    ends_at: datetime,
) -> tuple[bool, uuid.UUID | None]:
    """Whether this employee (plus a room, if the service needs one) is free
    for this window, and which room to actually use. Unlike the internal
    agenda -- where staff pick a specific room -- the client here only
    chooses a service/professional/time, so a free room (any one; Room is a
    generic interchangeable resource, see its model docstring) has to be
    found automatically. Built on appointment_service.has_conflict, the same
    check create_appointment itself runs before writing, so a slot shown as
    free here can never disagree with the write path's own judgment of it.
    """
    employee_busy = await appointment_service.has_conflict(
        session, tenant_id, employee_id=employee_id, room_id=None, starts_at=starts_at, ends_at=ends_at
    )
    if employee_busy:
        return (False, None)
    if not service.requires_room:
        return (True, None)

    rooms = await RoomRepository(session, tenant_id).list(is_active=True)
    for room in rooms:
        conflict = await appointment_service.has_conflict(
            session, tenant_id, employee_id=employee_id, room_id=room.id, starts_at=starts_at, ends_at=ends_at
        )
        if not conflict:
            return (True, room.id)
    return (False, None)


async def compute_availability(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    employee_id: uuid.UUID,
    service_id: uuid.UUID,
    on_date: date_,
) -> list[datetime]:
    company = await get_company(session, tenant_id)
    service = await _get_bookable_service(session, tenant_id, service_id)
    employee = await _get_qualified_employee(session, tenant_id, employee_id, service_id)

    tz = ZoneInfo(company.timezone)
    weekday = on_date.weekday()  # 0=Monday .. 6=Sunday, matches EmployeeAvailability.weekday
    windows = [w for w in employee.availability if w.weekday == weekday]
    if not windows:
        return []

    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=_SLOT_STEP_MINUTES)
    now = datetime.now(timezone.utc)

    available: list[datetime] = []
    for window in windows:
        window_start = datetime.combine(on_date, window.start_time, tzinfo=tz)
        window_end = datetime.combine(on_date, window.end_time, tzinfo=tz)
        slot_start = window_start
        while slot_start + duration <= window_end:
            slot_start_utc = slot_start.astimezone(timezone.utc)
            if slot_start_utc > now:
                slot_end_utc = (slot_start + duration).astimezone(timezone.utc)
                is_available, _ = await _has_capacity(
                    session,
                    tenant_id,
                    employee_id=employee_id,
                    service=service,
                    starts_at=slot_start_utc,
                    ends_at=slot_end_utc,
                )
                if is_available:
                    available.append(slot_start_utc)
            slot_start += step
    return available


async def _find_or_create_client(
    session: AsyncSession, tenant_id: uuid.UUID, *, name: str, phone: str, email: str | None
) -> Client:
    repo = ClientRepository(session, tenant_id)
    existing = await repo.list(phone=phone)
    if existing:
        # A repeat booker's existing record stays authoritative -- a typo'd
        # or shortened name typed into this form shouldn't silently overwrite
        # what staff may already have on file for this phone number.
        return existing[0]
    client = repo.add(Client(name=name, phone=phone, email=email))
    await session.flush()
    return client


async def create_booking(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    service_id: uuid.UUID,
    employee_id: uuid.UUID,
    starts_at: datetime,
    client_name: str,
    client_phone: str,
    client_email: str | None,
    notes: str | None,
    payment_method: PaymentMethodLiteral,
) -> PublicBookingResponse:
    company = await get_company(session, tenant_id)
    service = await _get_bookable_service(session, tenant_id, service_id)
    await _get_qualified_employee(session, tenant_id, employee_id, service_id)

    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    # A friendly pre-check to pick a room, same as compute_availability --
    # not the correctness guarantee. create_appointment below re-validates
    # with its own has_conflict call and is itself backed by the DB exclusion
    # constraints, so a slot taken between this check and that write still
    # fails safely (as a 409), just not with a room pre-selected for nothing.
    is_available, room_id = await _has_capacity(
        session, tenant_id, employee_id=employee_id, service=service, starts_at=starts_at, ends_at=ends_at
    )
    if not is_available:
        raise ConflictError("Este horário não está mais disponível")

    client = await _find_or_create_client(
        session, tenant_id, name=client_name, phone=client_phone, email=client_email
    )

    appointment = await appointment_service.create_appointment(
        session,
        tenant_id,
        client_id=client.id,
        employee_id=employee_id,
        service_id=service_id,
        starts_at=starts_at,
        room_id=room_id,
        source=AppointmentSource.PUBLIC_BOOKING,
        notes=notes,
    )
    # create_appointment just committed, which ends the transaction that
    # set_tenant_context's SET LOCAL was scoped to -- current_setting(...)
    # reverts to '' the instant that happens. Every other service function
    # in this codebase commits exactly once, as the last thing it does
    # before its session is discarded, so this has never come up before;
    # this is the first place that chains more than one committing call
    # (create_appointment, then confirm_appointment/create_deposit_charge,
    # then get_booking_status's own possible refresh_payment_status) on one
    # session, so every one of those commits must be followed by
    # re-asserting tenant context before the next tenant-scoped query, or it
    # 500s with "invalid input syntax for type uuid: ''" -- that's the RLS
    # policy's own current_setting(...)::uuid cast choking on the reverted
    # empty string, not a bug in whatever query happens to run next.
    await set_tenant_context(session, tenant_id)

    if service.deposit_required:
        await payment_service.create_deposit_charge(session, tenant_id, appointment.id, method=payment_method)
        await set_tenant_context(session, tenant_id)
    elif company.auto_confirm_public_bookings:
        await appointment_service.confirm_appointment(
            session, tenant_id, appointment.id, changed_by="public_booking_auto_confirm"
        )
        await set_tenant_context(session, tenant_id)

    return await get_booking_status(session, tenant_id, appointment.id)


async def get_booking_status(
    session: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID
) -> PublicBookingResponse:
    appointment = await appointment_service.get_appointment(session, tenant_id, appointment_id)

    payments = await PaymentRecordRepository(session, tenant_id).list(appointment_id=appointment_id)
    payment = payments[0] if payments else None
    if payment is not None and payment.status == PaymentStatus.PENDING and payment.provider_reference_id:
        # The public status page is polled instead of pushed to (no public
        # webhook target without a tunnel, see payment_service.py) -- so
        # polling this endpoint IS the refresh mechanism, same fallback
        # refresh_payment_status already provides for the authenticated side.
        payment = await payment_service.refresh_payment_status(session, tenant_id, payment.id)
        # refresh_payment_status just committed (it always does, given the
        # PENDING + provider_reference_id guard above) -- re-assert tenant
        # context before the query below, or it fails; see the matching
        # comment in create_booking for the full mechanism.
        await set_tenant_context(session, tenant_id)
        appointment = await appointment_service.get_appointment(session, tenant_id, appointment_id)

    service = appointment.service
    return PublicBookingResponse(
        id=appointment.id,
        status=appointment.status,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        service_name=service.name,
        employee_name=appointment.employee.name,
        deposit_required=service.deposit_required,
        deposit_amount=payment.amount if payment else None,
        payment_status=payment.status if payment else None,
        pix_qr_code=payment.pix_qr_code if payment else None,
        checkout_url=payment.checkout_url if payment else None,
    )
