import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory, set_tenant_context
from app.core.exceptions import ValidationError
from app.models.catalog import Service
from app.models.enums import AppointmentStatus, DepositType, PaymentMethod, PaymentProviderName, PaymentStatus, PaymentType
from app.models.payment import PaymentRecord
from app.providers.payments.base import PaymentMethodLiteral
from app.providers.payments.factory import get_payment_provider
from app.repositories.payment_repository import PaymentRecordRepository
from app.services import appointment_service

_CHARGE_STATUS_TO_PAYMENT_STATUS = {
    "pending": PaymentStatus.PENDING,
    "approved": PaymentStatus.APPROVED,
    "rejected": PaymentStatus.REJECTED,
}


@dataclass(frozen=True)
class DepositChargeResult:
    """pix_qr_code/checkout_url are transient (from the provider's response
    at charge-creation time, not persisted on PaymentRecord -- a QR code is
    only useful in the moment, not something to store as durable state), so
    this bundles them alongside the persisted record for the one response
    that actually needs to show them to the client.
    """

    record: PaymentRecord
    pix_qr_code: str | None
    checkout_url: str | None


def _compute_deposit_amount(service: Service) -> Decimal:
    if service.deposit_type == DepositType.FIXED_AMOUNT:
        return service.deposit_value
    if service.deposit_type == DepositType.PERCENTAGE:
        return (service.price * service.deposit_value / Decimal(100)).quantize(Decimal("0.01"))
    raise ValidationError("service has no valid deposit policy configured")


async def create_deposit_charge(
    session: AsyncSession, tenant_id: uuid.UUID, appointment_id: uuid.UUID, *, method: PaymentMethodLiteral
) -> DepositChargeResult:
    """Creates a PaymentRecord first (to get an id we control), then calls the
    provider with external_reference="{tenant_id}.{record_id}" -- this is
    what lets the webhook handler below resolve which tenant a notification
    belongs to without a URL slug (Mercado Pago webhooks are one global
    endpoint, unlike the WhatsApp webhook's per-tenant slugged URL), the
    same "embed routing info in something we control" pattern already used
    for refresh tokens and password reset tokens.
    """
    appointment = await appointment_service.get_appointment(session, tenant_id, appointment_id)
    service = appointment.service
    if not service.deposit_required:
        raise ValidationError("this service does not require a deposit")

    amount = _compute_deposit_amount(service)
    is_full = service.deposit_type == DepositType.PERCENTAGE and service.deposit_value == Decimal(100)

    provider_name = (
        PaymentProviderName.MERCADOPAGO if get_settings().payment_provider == "mercadopago" else PaymentProviderName.MOCK
    )

    record = PaymentRecordRepository(session, tenant_id).add(
        PaymentRecord(
            appointment_id=appointment_id,
            provider=provider_name,
            amount=amount,
            type=PaymentType.DEPOSIT_FULL if is_full else PaymentType.DEPOSIT_PARTIAL,
            method=PaymentMethod(method),
            status=PaymentStatus.PENDING,
        )
    )
    await session.flush()  # populates record.id, needed for external_reference below

    provider = get_payment_provider()
    charge = await provider.create_charge(
        amount=amount,
        method=method,
        external_reference=f"{tenant_id}.{record.id}",
        description=f"Sinal - {service.name}",
    )
    record.provider_reference_id = charge.provider_reference_id
    record.pix_qr_code = charge.pix_qr_code
    record.checkout_url = charge.checkout_url
    record.status = _CHARGE_STATUS_TO_PAYMENT_STATUS[charge.status]
    if record.status == PaymentStatus.APPROVED:
        record.paid_at = datetime.now(timezone.utc)
        if appointment.status == AppointmentStatus.PENDING:
            await appointment_service.confirm_appointment(
                session, tenant_id, appointment_id, changed_by="payment_provider"
            )

    await session.commit()
    return DepositChargeResult(record=record, pix_qr_code=charge.pix_qr_code, checkout_url=charge.checkout_url)


async def _apply_status_and_maybe_confirm(
    session: AsyncSession, tenant_id: uuid.UUID, record: PaymentRecord, new_status: PaymentStatus
) -> None:
    record.status = new_status
    if new_status == PaymentStatus.APPROVED:
        record.paid_at = datetime.now(timezone.utc)
    await session.flush()

    if new_status == PaymentStatus.APPROVED:
        appointment = await appointment_service.get_appointment(session, tenant_id, record.appointment_id)
        if appointment.status == AppointmentStatus.PENDING:
            await appointment_service.confirm_appointment(
                session, tenant_id, record.appointment_id, changed_by="payment_provider"
            )


async def refresh_payment_status(session: AsyncSession, tenant_id: uuid.UUID, payment_record_id: uuid.UUID) -> PaymentRecord:
    """Polls the provider directly rather than waiting for a webhook --
    useful for local/sandbox testing, where Mercado Pago's real webhook
    delivery can't reach this server without a public URL (ngrok or
    similar), which this build deliberately doesn't set up. Real production
    use should still rely on the webhook for low-latency updates; this is
    the fallback/manual-refresh path, not a replacement for it.
    """
    repo = PaymentRecordRepository(session, tenant_id)
    record = await repo.get(payment_record_id)
    if record is None:
        raise ValidationError("payment record not found")
    if record.status != PaymentStatus.PENDING or not record.provider_reference_id:
        return record

    provider = get_payment_provider()
    charge = await provider.get_charge_status(record.provider_reference_id)
    await _apply_status_and_maybe_confirm(session, tenant_id, record, _CHARGE_STATUS_TO_PAYMENT_STATUS[charge.status])
    await session.commit()
    return record


async def handle_mercadopago_webhook(payload: dict, headers: dict) -> None:
    """No tenant_id parameter: unlike the WhatsApp webhook (resolved from a
    per-tenant URL slug), Mercado Pago's webhook is one global endpoint, so
    tenant has to come out of the notification's own external_reference
    (see create_deposit_charge) -- meaning this function must open its own
    session once that's parsed, the same shape as workers/reminders.py's
    per-tenant scan, for the same underlying reason (no tenant known before
    this function runs).
    """
    provider = get_payment_provider()
    event = await provider.parse_webhook(payload, headers)
    if event is None or not event.external_reference:
        return

    try:
        tenant_id_str, record_id_str = event.external_reference.split(".", 1)
        tenant_id = uuid.UUID(tenant_id_str)
        record_id = uuid.UUID(record_id_str)
    except ValueError:
        return

    async with async_session_factory() as session:
        await set_tenant_context(session, tenant_id)
        record = await PaymentRecordRepository(session, tenant_id).get(record_id)
        if record is None:
            return

        await _apply_status_and_maybe_confirm(session, tenant_id, record, _CHARGE_STATUS_TO_PAYMENT_STATUS[event.status])
        await session.commit()
