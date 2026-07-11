import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.appointment import Appointment, WaitlistEntry
from app.models.enums import NotificationType, WaitlistStatus
from app.repositories.client_repository import ClientRepository
from app.repositories.waitlist_repository import WaitlistRepository
from app.services import notification_service
from app.services.notification_service import NotificationContext


async def join_waitlist(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    client_id: uuid.UUID,
    service_id: uuid.UUID,
    preferred_window_start: datetime,
    preferred_window_end: datetime,
    preferred_employee_id: uuid.UUID | None = None,
) -> WaitlistEntry:
    entry = WaitlistRepository(session, tenant_id).add(
        WaitlistEntry(
            client_id=client_id,
            service_id=service_id,
            preferred_employee_id=preferred_employee_id,
            preferred_window_start=preferred_window_start,
            preferred_window_end=preferred_window_end,
            status=WaitlistStatus.WAITING,
        )
    )
    await session.commit()
    return entry


async def list_waitlist(session: AsyncSession, tenant_id: uuid.UUID) -> list[WaitlistEntry]:
    return await WaitlistRepository(session, tenant_id).list(status=WaitlistStatus.WAITING)


async def cancel_waitlist_entry(session: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    entry = await WaitlistRepository(session, tenant_id).get(entry_id)
    if entry is None:
        raise NotFoundError("waitlist entry not found")
    entry.status = WaitlistStatus.CANCELLED
    await session.commit()


async def promote_next_match(session: AsyncSession, tenant_id: uuid.UUID, freed_appointment: Appointment) -> WaitlistEntry | None:
    """Called synchronously from appointment_service.cancel_appointment, the
    moment a slot frees up -- lower latency than waiting for a periodic
    scan, and simpler than coordinating with the reminder scan's schedule.
    Marks the match PROMOTED and notifies them; does not auto-book a new
    Appointment for them (that needs their confirmation first -- see
    notification_service's WAITLIST_PROMOTION message, which asks them to
    reply to confirm). Converting an accepted offer into a real appointment
    happens through the normal appointment creation path (staff-created, or
    eventually the inbound WhatsApp webhook), not through this function.

    Uses flush(), not commit(): always called as a nested step from
    cancel_appointment's unit of work, which owns the single final commit.
    """
    repo = WaitlistRepository(session, tenant_id)
    entry = await repo.find_oldest_match(
        service_id=freed_appointment.service_id,
        employee_id=freed_appointment.employee_id,
        slot_start=freed_appointment.starts_at,
    )
    if entry is None:
        return None

    entry.status = WaitlistStatus.PROMOTED
    await session.flush()

    client = await ClientRepository(session, tenant_id).get(entry.client_id)
    await notification_service.send_notification(
        session,
        tenant_id,
        appointment_id=None,
        client_id=entry.client_id,
        notification_type=NotificationType.WAITLIST_PROMOTION,
        context=NotificationContext(
            client_name=client.name if client else "",
            client_phone=client.phone if client else "",
            service_name=freed_appointment.service.name,
            employee_name=freed_appointment.employee.name,
            starts_at=freed_appointment.starts_at,
        ),
    )
    return entry
