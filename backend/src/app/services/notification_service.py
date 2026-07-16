import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_secret
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.models.notification import NotificationLog
from app.models.tenant import Company
from app.providers.email.base import SmtpConfig
from app.providers.email.factory import get_email_provider
from app.providers.notifications.factory import get_notification_provider
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger("app.notifications")


@dataclass(frozen=True)
class NotificationContext:
    """Deliberately not tied to an Appointment ORM object: a waitlist
    promotion notifies about a slot that just freed up, for a client who
    doesn't have an appointment yet (that's the whole point -- they're
    offered it, not auto-booked into it), so every notification type needs
    to work from these plain fields instead.
    """

    client_name: str
    client_phone: str
    service_name: str
    employee_name: str
    starts_at: datetime
    # Optional and last so every existing positional/keyword construction
    # site keeps working unchanged -- only sites that also want the email
    # channel need to pass it (see appointment_service.py, waitlist_service.py,
    # workers/reminders.py).
    client_email: str | None = None


_MESSAGE_BUILDERS = {
    # Both reminders state the exact date/time rather than a relative word
    # like "amanhã"/"em 2 horas" -- each company can configure its own
    # reminder_first_hours/reminder_second_hours (see workers/reminders.py),
    # so a hardcoded relative phrase would go stale for any tenant that
    # changes the defaults.
    NotificationType.REMINDER_24H: lambda ctx: (
        f"Olá {ctx.client_name}! Lembrete: você tem {ctx.service_name} agendado para "
        f"{ctx.starts_at.strftime('%d/%m às %H:%M')}, com {ctx.employee_name}. "
        f"Responda 1 para confirmar ou 2 para cancelar."
    ),
    NotificationType.REMINDER_2H: lambda ctx: (
        f"Olá {ctx.client_name}! Seu horário de {ctx.service_name} é às "
        f"{ctx.starts_at.strftime('%H:%M')} de {ctx.starts_at.strftime('%d/%m')}. Te esperamos!"
    ),
    NotificationType.CONFIRMATION: lambda ctx: (
        f"Agendamento confirmado: {ctx.service_name} em {ctx.starts_at.strftime('%d/%m às %H:%M')} com {ctx.employee_name}."
    ),
    NotificationType.CANCELLATION: lambda ctx: (
        f"Seu agendamento de {ctx.service_name} em {ctx.starts_at.strftime('%d/%m às %H:%M')} foi cancelado."
    ),
    NotificationType.RESCHEDULE: lambda ctx: (
        f"Seu agendamento de {ctx.service_name} foi remarcado para {ctx.starts_at.strftime('%d/%m às %H:%M')}."
    ),
    NotificationType.WAITLIST_PROMOTION: lambda ctx: (
        f"Boa notícia, {ctx.client_name}! Um horário abriu para {ctx.service_name} em "
        f"{ctx.starts_at.strftime('%d/%m às %H:%M')} com {ctx.employee_name}. "
        f"Responda 1 para confirmar esse horário."
    ),
}

# Email reuses the WhatsApp message text as its body (see _MESSAGE_BUILDERS
# above) -- only the subject line differs, so no separate copy to maintain.
_EMAIL_SUBJECT_BUILDERS = {
    NotificationType.REMINDER_24H: lambda ctx: f"Lembrete: {ctx.service_name} em breve",
    NotificationType.REMINDER_2H: lambda ctx: f"Lembrete: {ctx.service_name} está chegando",
    NotificationType.CONFIRMATION: lambda ctx: f"Agendamento confirmado — {ctx.service_name}",
    NotificationType.CANCELLATION: lambda ctx: f"Agendamento cancelado — {ctx.service_name}",
    NotificationType.RESCHEDULE: lambda ctx: f"Agendamento remarcado — {ctx.service_name}",
    NotificationType.WAITLIST_PROMOTION: lambda ctx: "Um horário abriu para você!",
}

# Only reminders need the idempotency guard below: they're the one
# notification type a periodic scan might see and enqueue more than once
# for the same appointment. Action-triggered types (confirm/cancel/
# reschedule/waitlist) are each fired by one discrete user action per call,
# and for RESCHEDULE specifically, gating on "already sent for this
# appointment_id" would be actively wrong -- an appointment can legitimately
# be rescheduled more than once, and the client should hear about each move,
# not just the first.
_IDEMPOTENCY_GUARDED_TYPES = {NotificationType.REMINDER_24H, NotificationType.REMINDER_2H}


async def send_notification(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    appointment_id: uuid.UUID | None,
    client_id: uuid.UUID,
    notification_type: NotificationType,
    context: NotificationContext,
    channel: NotificationChannel = NotificationChannel.WHATSAPP,
) -> NotificationLog | None:
    """Returns None (no-op) only if notification_type is a reminder AND this
    (appointment_id, notification_type) pair was already sent -- see
    _IDEMPOTENCY_GUARDED_TYPES above for why only reminders are guarded this
    way. appointment_id is nullable (a waitlist promotion notification isn't
    about an existing appointment).

    Uses flush(), not commit(): this is always called as a nested step from
    something else's unit of work (a status transition, a waitlist
    promotion, a worker job scanning for reminders), and that caller is
    responsible for the single final commit -- see
    core/database.py:get_tenant_db's docstring for why an intermediate
    commit followed by more querying breaks RLS context.
    """
    repo = NotificationRepository(session, tenant_id)
    if (
        notification_type in _IDEMPOTENCY_GUARDED_TYPES
        and appointment_id is not None
        and await repo.already_sent(appointment_id, notification_type)
    ):
        return None

    message = _MESSAGE_BUILDERS[notification_type](context)
    provider = get_notification_provider()
    result = await provider.send_text(to_phone=context.client_phone, message=message, correlation_id=str(appointment_id or client_id))

    log = repo.add(
        NotificationLog(
            appointment_id=appointment_id,
            client_id=client_id,
            channel=channel,
            notification_type=notification_type,
            status=NotificationStatus.SENT,
            provider_message_id=result.provider_message_id,
            sent_at=datetime.now(timezone.utc),
            payload_snapshot={"message": message},
        )
    )

    await _send_email_if_configured(
        session,
        tenant_id,
        appointment_id=appointment_id,
        client_id=client_id,
        notification_type=notification_type,
        context=context,
    )

    await session.flush()
    return log


async def _send_email_if_configured(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    appointment_id: uuid.UUID | None,
    client_id: uuid.UUID,
    notification_type: NotificationType,
    context: NotificationContext,
) -> None:
    """Second, independent channel alongside WhatsApp above -- logged as its
    own NotificationLog row (channel=EMAIL), same (appointment_id,
    notification_type) pair. The idempotency guard in send_notification()
    already covers this: both channels are attempted inside the same call,
    so a later duplicate call for the same reminder still no-ops entirely
    (deliberate scope boundary, not a gap -- there's no per-channel retry in
    this pass). A failure here (bad credentials, mail server down) must
    never take down the WhatsApp send above or the caller's transaction --
    caught and logged as a FAILED row instead of propagating.
    """
    if context.client_email is None:
        return

    company = await session.get(Company, tenant_id)
    if company is None or not (
        company.smtp_host and company.smtp_username and company.smtp_password_encrypted and company.smtp_from_email
    ):
        return

    repo = NotificationRepository(session, tenant_id)
    subject = _EMAIL_SUBJECT_BUILDERS[notification_type](context)
    body = _MESSAGE_BUILDERS[notification_type](context)

    try:
        smtp_config = SmtpConfig(
            host=company.smtp_host,
            port=company.smtp_port or 587,
            username=company.smtp_username,
            password=decrypt_secret(company.smtp_password_encrypted),
            from_email=company.smtp_from_email,
        )
        await get_email_provider().send(to=context.client_email, subject=subject, body=body, smtp_config=smtp_config)
        status = NotificationStatus.SENT
    except Exception:
        logger.exception(
            "email notification failed for tenant_id=%s appointment_id=%s notification_type=%s",
            tenant_id,
            appointment_id,
            notification_type,
        )
        status = NotificationStatus.FAILED

    repo.add(
        NotificationLog(
            appointment_id=appointment_id,
            client_id=client_id,
            channel=NotificationChannel.EMAIL,
            notification_type=notification_type,
            status=status,
            sent_at=datetime.now(timezone.utc) if status == NotificationStatus.SENT else None,
            payload_snapshot={"subject": subject, "message": body},
        )
    )
