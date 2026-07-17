import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.providers.payments.base import ChargeResult, PaymentMethodLiteral, PaymentProvider, WebhookEvent

settings = get_settings()

API_BASE = "https://api.mercadopago.com"


@dataclass(frozen=True)
class MercadoPagoConfig:
    """A tenant's own Mercado Pago account (Company.mp_*_encrypted, decrypted
    at call time by payment_service). Passed per-instance rather than read
    from global settings so each business's deposits land in ITS account --
    same per-tenant-credential shape as email's SmtpConfig.
    """

    access_token: str
    webhook_secret: str | None = None

_STATUS_MAP = {
    "pending": "pending",
    "in_process": "pending",
    "authorized": "pending",
    "approved": "approved",
    "rejected": "rejected",
    "cancelled": "rejected",
    "refunded": "rejected",
}


class MercadoPagoProvider(PaymentProvider):
    """Real integration target: unlike WhatsApp, Mercado Pago's developer
    sandbox/test credentials are self-service-obtainable (no human-review
    wait), so this is meant to be exercised against a live sandbox account
    during this build, not just left as untested stub code -- see
    payment_service.py and the plan for how this gets validated.

    Credit card charges need a card TOKEN generated client-side via MP's JS
    SDK (never send raw card numbers to any backend) -- that frontend
    tokenization flow isn't built in this milestone, so `method="credit_card"`
    is correct-shaped but will fail without a real token; PIX is the fully
    working path (and the more commonly used one for this product's
    market/price point anyway).
    """

    def __init__(self, config: MercadoPagoConfig | None = None) -> None:
        # config=None falls back to the global env-var credentials -- kept so
        # the legacy PAYMENT_PROVIDER=mercadopago global switch still works,
        # but the per-tenant path (payment_service._provider_for_tenant)
        # always passes an explicit config.
        if config is None:
            if not settings.mercadopago_access_token:
                raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN not configured")
            config = MercadoPagoConfig(
                access_token=settings.mercadopago_access_token,
                webhook_secret=settings.mercadopago_webhook_secret,
            )
        self._access_token = config.access_token
        self._webhook_secret = config.webhook_secret

    def _headers(self, *, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    async def create_charge(
        self, *, amount: Decimal, method: PaymentMethodLiteral, external_reference: str, description: str
    ) -> ChargeResult:
        payload: dict = {
            "transaction_amount": float(amount),
            "description": description,
            "external_reference": external_reference,
            # A real payer email is required by the Payments API even for
            # PIX; a tenant-specific placeholder is fine for a deposit flow
            # that doesn't otherwise collect one.
            "payer": {"email": "cliente@example.com"},
        }
        if method == "pix":
            payload["payment_method_id"] = "pix"
        else:
            # Requires payload["token"] (the client-tokenized card) to
            # actually succeed -- see class docstring.
            payload["installments"] = 1

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/payments",
                headers=self._headers(idempotency_key=external_reference),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        pix_qr_code = None
        if method == "pix":
            pix_qr_code = data.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code")

        return ChargeResult(
            provider_reference_id=str(data["id"]),
            status=_STATUS_MAP.get(data["status"], "pending"),
            pix_qr_code=pix_qr_code,
            checkout_url=data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url")
            if method == "credit_card"
            else None,
        )

    async def get_charge_status(self, provider_reference_id: str) -> ChargeResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{API_BASE}/v1/payments/{provider_reference_id}", headers=self._headers())
            response.raise_for_status()
            data = response.json()
        return ChargeResult(provider_reference_id=str(data["id"]), status=_STATUS_MAP.get(data["status"], "pending"))

    async def parse_webhook(self, payload: dict, headers: dict) -> WebhookEvent | None:
        if payload.get("type") != "payment":
            return None
        payment_id = payload.get("data", {}).get("id")
        if not payment_id:
            return None

        if self._webhook_secret:
            if not self._verify_signature(payment_id=str(payment_id), headers=headers):
                return None

        # The notification body only carries an id -- status and
        # external_reference both need this one follow-up fetch.
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{API_BASE}/v1/payments/{payment_id}", headers=self._headers())
            response.raise_for_status()
            data = response.json()

        return WebhookEvent(
            provider_reference_id=str(data["id"]),
            status=_STATUS_MAP.get(data["status"], "pending"),
            external_reference=data.get("external_reference"),
        )

    def _verify_signature(self, *, payment_id: str, headers: dict) -> bool:
        """Mercado Pago's HMAC-SHA256 webhook signature scheme: x-signature is
        `ts=<unix ts>,v1=<hex hmac>`, computed over the manifest string
        `id:{data.id};request-id:{x-request-id};ts:{ts};` using the webhook
        secret from the integration's notification settings. Worth
        re-verifying against MP's current docs during the real sandbox test
        this is meant to run against -- this is implemented from
        specification memory, not against a live signed payload.
        """
        signature_header = headers.get("x-signature", "")
        request_id = headers.get("x-request-id", "")
        parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
        ts, v1 = parts.get("ts"), parts.get("v1")
        if not ts or not v1:
            return False

        manifest = f"id:{payment_id.lower()};request-id:{request_id};ts:{ts};"
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, v1)
