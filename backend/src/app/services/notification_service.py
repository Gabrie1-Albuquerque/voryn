import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.models.notification import NotificationLog
from app.providers.notifications.factory import get_notification_provider
from app.repositories.notification_repository import NotificationRepository


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


_MESSAGE_BUILDERS = {
    NotificationType.REMINDER_24H: lambda ctx: (
        f"Olá {ctx.client_name}! Lembrete: você tem {ctx.service_name} agendado para amanhã, "
        f"{ctx.starts_at.strftime('%d/%m às %H:%M')}, com {ctx.employee_name}. "
        f"Responda 1 para confirmar ou 2 para cancelar."
    ),
    NotificationType.REMINDER_2H: lambda ctx: (
        f"Olá {ctx.client_name}! Seu horário de {ctx.service_name} é hoje às {ctx.starts_at.strftime('%H:%M')}, "
        f"em cerca de 2 horas. Te esperamos!"
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
    await session.flush()
    return log
