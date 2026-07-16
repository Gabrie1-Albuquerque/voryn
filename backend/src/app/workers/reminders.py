"""RQ job: scans every active tenant for confirmed appointments starting
around each company's configured reminder offsets (Company.reminder_first_hours/
reminder_second_hours, defaulting to 24h/2h) and sends reminders. RQ workers
run synchronous Python functions, so this bridges into the async stack via
asyncio.run -- there's no event loop already running in an RQ worker
process to piggyback on, unlike request handling.

Runs per-tenant (not one cross-tenant query): the RLS/SET LOCAL model this
whole app relies on requires a known tenant_id before any tenant-owned table
can be queried at all (see core/database.py:set_tenant_context), and this
job is the one place that legitimately needs to visit every tenant in turn
rather than always having exactly one known upfront. Iterating tenants and
re-scoping per iteration keeps this on the same RLS-protected path as
everything else, rather than adding a second cross-tenant bypass alongside
the login one (core/database.py's find_login_credentials).
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory, set_tenant_context
from app.models.enums import NotificationType
from app.models.tenant import Company
from app.repositories.appointment_repository import AppointmentRepository
from app.services import notification_service
from app.services.notification_service import NotificationContext

logger = logging.getLogger("app.workers.reminders")
settings = get_settings()


def scan_and_enqueue_reminders() -> None:
    """Sync entry point registered with rq-scheduler (see workers/scheduler.py)."""
    asyncio.run(_scan_and_enqueue_reminders_async())


async def _scan_and_enqueue_reminders_async() -> None:
    async with async_session_factory() as session:
        # companies has no RLS (it's the tenant root, not tenant-owned -- see
        # migration 0001), so this cross-tenant read needs no special context.
        result = await session.execute(
            select(Company.id, Company.reminder_first_hours, Company.reminder_second_hours).where(
                Company.is_active.is_(True)
            )
        )
        tenants = list(result.all())

    for tenant_id, first_hours, second_hours in tenants:
        try:
            await _scan_tenant(tenant_id, first_hours, second_hours)
        except Exception:
            # One tenant's failure (a bad provider config, a transient
            # network error) must not stop the scan for every other tenant.
            logger.exception("reminder scan failed for tenant_id=%s", tenant_id)


async def _scan_tenant(tenant_id: uuid.UUID, first_hours: int, second_hours: int) -> None:
    now = datetime.now(timezone.utc)
    reminder_windows = [
        (NotificationType.REMINDER_24H, timedelta(hours=first_hours)),
        (NotificationType.REMINDER_2H, timedelta(hours=second_hours)),
    ]
    async with async_session_factory() as session:
        await set_tenant_context(session, tenant_id)
        repo = AppointmentRepository(session, tenant_id)

        for notification_type, offset in reminder_windows:
            window_start = now + offset
            window_end = window_start + timedelta(minutes=settings.reminder_scan_interval_minutes)
            appointments = await repo.list_confirmed_starting_in_window(window_start, window_end)

            for appointment in appointments:
                await notification_service.send_notification(
                    session,
                    tenant_id,
                    appointment_id=appointment.id,
                    client_id=appointment.client_id,
                    notification_type=notification_type,
                    context=NotificationContext(
                        client_name=appointment.client.name,
                        client_phone=appointment.client.phone,
                        client_email=appointment.client.email,
                        service_name=appointment.service.name,
                        employee_name=appointment.employee.name,
                        starts_at=appointment.starts_at,
                    ),
                )

        await session.commit()
