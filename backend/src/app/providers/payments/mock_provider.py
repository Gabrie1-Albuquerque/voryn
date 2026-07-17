import logging
import uuid
from decimal import Decimal

from app.providers.payments.base import ChargeResult, PaymentMethodLiteral, PaymentProvider, WebhookEvent

logger = logging.getLogger("app.payments")


class MockPaymentProvider(PaymentProvider):
    """Local-dev default: simulates a charge succeeding immediately, with no
    external call -- lets the whole "deposit required to confirm a booking"
    flow (payment_service.py, the public booking page in milestone 9) be
    built and demoed end-to-end with zero credentials. Real webhook delivery
    obviously can't be simulated by this provider itself; payment_service's
    create_deposit_charge auto-approves synchronously instead of waiting for
    one, which is the correct stand-in for what a webhook would otherwise do.
    """

    async def create_charge(
        self, *, amount: Decimal, method: PaymentMethodLiteral, external_reference: str, description: str
    ) -> ChargeResult:
        reference = f"mock-{uuid.uuid4()}"
        logger.info(
            "MOCK CHARGE amount=%s method=%s external_reference=%s description=%r -> auto-approved (%s)",
            amount,
            method,
            external_reference,
            description,
            reference,
        )
        return ChargeResult(
            provider_reference_id=reference,
            status="approved",
            pix_qr_code="00020126-mock-pix-payload" if method == "pix" else None,
            checkout_url="https://mock-checkout.local/pay/" + reference if method == "credit_card" else None,
        )

    async def get_charge_status(self, provider_reference_id: str) -> ChargeResult:
        return ChargeResult(provider_reference_id=provider_reference_id, status="approved")

    async def parse_webhook(self, payload: dict, headers: dict) -> WebhookEvent | None:
        # Always None: the mock never trusts an inbound webhook. The global
        # /webhooks/mercadopago endpoint runs the global provider, which is
        # this mock in production (PAYMENT_PROVIDER=mock) -- if it parsed the
        # body, anyone could POST {status:"approved", external_reference:
        # "{tenant}.{record}"} to confirm an unpaid appointment. Mock already
        # auto-approves at charge creation, so it has no legitimate webhook to
        # process. Real per-tenant Mercado Pago uses the slugged endpoint,
        # which re-fetches status from MP's authenticated API instead.
        return None
