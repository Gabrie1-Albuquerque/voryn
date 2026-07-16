import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType, WaitlistStatus
from app.models.notification import NotificationLog
from app.repositories.waitlist_repository import WaitlistRepository
from app.schemas.catalog import ServiceCreateRequest
from app.schemas.client import ClientCreateRequest, ClientUpdateRequest
from app.schemas.company import CompanyUpdateRequest
from app.schemas.employee import EmployeeCreateRequest
from app.services import (
    appointment_service,
    catalog_service,
    client_service,
    company_service,
    employee_service,
    notification_service,
    waitlist_service,
)
from app.services.notification_service import NotificationContext

BASE_START = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)


async def _seed(db_session: AsyncSession, tenant_id: uuid.UUID) -> dict:
    service = await catalog_service.create_service(
        db_session, tenant_id, ServiceCreateRequest(name="Corte", duration_minutes=60, price=Decimal("50"))
    )
    employee = await employee_service.create_employee(db_session, tenant_id, EmployeeCreateRequest(name="Maria"))
    client_a = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Joana", phone="5511999998888")
    )
    client_b = await client_service.create_client(
        db_session, tenant_id, ClientCreateRequest(name="Paula", phone="5511999997777")
    )
    return {"service": service, "employee": employee, "client_a": client_a, "client_b": client_b}


async def _configure_smtp(db_session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Goes through the real update_company path (encrypts the password),
    not a raw column write -- exercises the exact code the settings screen
    calls.
    """
    await company_service.update_company(
        db_session,
        tenant_id,
        CompanyUpdateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="contato@salao.example.com",
            smtp_password="senha-de-app-fake",
            smtp_from_email="contato@salao.example.com",
        ),
    )


async def _notification_count(
    session: AsyncSession, tenant_id: uuid.UUID, appointment_id, notification_type, channel=None
) -> int:
    stmt = select(NotificationLog).where(
        NotificationLog.tenant_id == tenant_id,
        NotificationLog.appointment_id == appointment_id,
        NotificationLog.notification_type == notification_type,
    )
    if channel is not None:
        stmt = stmt.where(NotificationLog.channel == channel)
    result = await session.execute(stmt)
    return len(result.scalars().all())


@pytest.mark.asyncio
async def test_confirming_appointment_sends_confirmation_notification(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    # STAFF-sourced appointments are auto-confirmed by create_appointment itself.
    count = await _notification_count(db_session, tenant_id, appointment.id, NotificationType.CONFIRMATION)
    assert count == 1


@pytest.mark.asyncio
async def test_cancelling_sends_cancellation_notification(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    await appointment_service.cancel_appointment(db_session, tenant_id, appointment.id, changed_by="staff")

    count = await _notification_count(db_session, tenant_id, appointment.id, NotificationType.CANCELLATION)
    assert count == 1


@pytest.mark.asyncio
async def test_rescheduling_twice_sends_two_notifications(db_session: AsyncSession, make_tenant):
    """Regression guard for the idempotency design flaw found while
    building this: gating RESCHEDULE on "already sent for this appointment"
    would silently swallow the notification for a second reschedule.
    """
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    await appointment_service.reschedule_appointment(
        db_session, tenant_id, appointment.id, new_starts_at=BASE_START + timedelta(days=1), changed_by="staff"
    )
    await appointment_service.reschedule_appointment(
        db_session, tenant_id, appointment.id, new_starts_at=BASE_START + timedelta(days=2), changed_by="staff"
    )

    count = await _notification_count(db_session, tenant_id, appointment.id, NotificationType.RESCHEDULE)
    assert count == 2


@pytest.mark.asyncio
async def test_reminder_notification_is_idempotent(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    context = NotificationContext(
        client_name="Joana", client_phone="5511999998888", service_name="Corte", employee_name="Maria", starts_at=BASE_START
    )
    first = await notification_service.send_notification(
        db_session,
        tenant_id,
        appointment_id=appointment.id,
        client_id=seed["client_a"].id,
        notification_type=NotificationType.REMINDER_24H,
        context=context,
    )
    second = await notification_service.send_notification(
        db_session,
        tenant_id,
        appointment_id=appointment.id,
        client_id=seed["client_a"].id,
        notification_type=NotificationType.REMINDER_24H,
        context=context,
    )
    await db_session.commit()

    assert first is not None
    assert second is None  # idempotent no-op on the second call
    count = await _notification_count(db_session, tenant_id, appointment.id, NotificationType.REMINDER_24H)
    assert count == 1


@pytest.mark.asyncio
async def test_join_waitlist_creates_waiting_entry(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    entry = await waitlist_service.join_waitlist(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        service_id=seed["service"].id,
        preferred_window_start=BASE_START - timedelta(hours=1),
        preferred_window_end=BASE_START + timedelta(hours=1),
    )
    assert entry.status == WaitlistStatus.WAITING

    waiting = await waitlist_service.list_waitlist(db_session, tenant_id)
    assert len(waiting) == 1


@pytest.mark.asyncio
async def test_cancelling_appointment_promotes_matching_waitlist_entry(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )
    entry = await waitlist_service.join_waitlist(
        db_session,
        tenant_id,
        client_id=seed["client_b"].id,
        service_id=seed["service"].id,
        preferred_window_start=BASE_START - timedelta(hours=2),
        preferred_window_end=BASE_START + timedelta(hours=2),
    )

    await appointment_service.cancel_appointment(db_session, tenant_id, appointment.id, changed_by="staff")

    refreshed = await WaitlistRepository(db_session, tenant_id).get(entry.id)
    assert refreshed.status == WaitlistStatus.PROMOTED

    # appointment_id is None for waitlist promotion notifications (see
    # notification_service's docstring), so query by client instead.
    result = await db_session.execute(
        select(NotificationLog).where(
            NotificationLog.tenant_id == tenant_id,
            NotificationLog.client_id == seed["client_b"].id,
            NotificationLog.notification_type == NotificationType.WAITLIST_PROMOTION,
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_cancelling_with_no_waitlist_match_does_not_crash(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    # No waitlist entries exist at all -- should cancel cleanly, no promotion.
    result = await appointment_service.cancel_appointment(db_session, tenant_id, appointment.id, changed_by="staff")
    assert result.status.value == "cancelled"


@pytest.mark.asyncio
async def test_confirmation_sends_email_when_smtp_and_client_email_configured(
    db_session: AsyncSession, make_tenant
):
    tenant_id = await make_tenant()
    await _configure_smtp(db_session, tenant_id)
    seed = await _seed(db_session, tenant_id)
    await client_service.update_client(
        db_session, tenant_id, seed["client_a"].id, ClientUpdateRequest(email="joana@example.com")
    )

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    whatsapp_count = await _notification_count(
        db_session, tenant_id, appointment.id, NotificationType.CONFIRMATION, channel=NotificationChannel.WHATSAPP
    )
    email_count = await _notification_count(
        db_session, tenant_id, appointment.id, NotificationType.CONFIRMATION, channel=NotificationChannel.EMAIL
    )
    assert whatsapp_count == 1
    assert email_count == 1


@pytest.mark.asyncio
async def test_confirmation_skips_email_when_smtp_not_configured(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    seed = await _seed(db_session, tenant_id)
    await client_service.update_client(
        db_session, tenant_id, seed["client_a"].id, ClientUpdateRequest(email="joana@example.com")
    )

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    email_count = await _notification_count(
        db_session, tenant_id, appointment.id, NotificationType.CONFIRMATION, channel=NotificationChannel.EMAIL
    )
    assert email_count == 0


@pytest.mark.asyncio
async def test_confirmation_skips_email_when_client_has_no_email(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    await _configure_smtp(db_session, tenant_id)
    seed = await _seed(db_session, tenant_id)
    # client_a has no email (see _seed) -- SMTP configured on the company
    # side alone must not be enough to attempt a send.

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    email_count = await _notification_count(
        db_session, tenant_id, appointment.id, NotificationType.CONFIRMATION, channel=NotificationChannel.EMAIL
    )
    assert email_count == 0


@pytest.mark.asyncio
async def test_email_failure_does_not_break_whatsapp_or_the_transaction(
    db_session: AsyncSession, make_tenant, monkeypatch
):
    tenant_id = await make_tenant()
    await _configure_smtp(db_session, tenant_id)
    seed = await _seed(db_session, tenant_id)
    await client_service.update_client(
        db_session, tenant_id, seed["client_a"].id, ClientUpdateRequest(email="joana@example.com")
    )

    class _BrokenEmailProvider:
        async def send(self, **kwargs):
            raise RuntimeError("mail server unreachable")

    monkeypatch.setattr(notification_service, "SmtpEmailProvider", _BrokenEmailProvider)

    appointment = await appointment_service.create_appointment(
        db_session,
        tenant_id,
        client_id=seed["client_a"].id,
        employee_id=seed["employee"].id,
        service_id=seed["service"].id,
        starts_at=BASE_START,
    )

    whatsapp_count = await _notification_count(
        db_session, tenant_id, appointment.id, NotificationType.CONFIRMATION, channel=NotificationChannel.WHATSAPP
    )
    assert whatsapp_count == 1  # unaffected by the email provider raising

    result = await db_session.execute(
        select(NotificationLog).where(
            NotificationLog.tenant_id == tenant_id,
            NotificationLog.appointment_id == appointment.id,
            NotificationLog.notification_type == NotificationType.CONFIRMATION,
            NotificationLog.channel == NotificationChannel.EMAIL,
        )
    )
    email_log = result.scalar_one()
    assert email_log.status == NotificationStatus.FAILED
