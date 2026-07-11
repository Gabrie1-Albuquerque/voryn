import httpx

from app.core.config import get_settings
from app.providers.notifications.base import InboundMessage, NotificationProvider, ProviderSendResult

settings = get_settings()


class ZApiProvider(NotificationProvider):
    """Z-API: a Brazilian WhatsApp BSP many local salons/clinics already use
    instead of Meta's official Cloud API -- it pairs with a real WhatsApp
    number like WhatsApp Web rather than requiring Meta Business
    verification and template approval, which is why it's a common
    alternative for small businesses in this exact market. Same
    can't-test-without-a-real-account caveat as the Cloud API applies here
    too, though the approval process itself is lighter-weight.

    Unlike the Cloud API, Z-API sends free-form text directly (no template
    system to work around), which is simpler and is why this is arguably
    the more realistic default for the Fase 1 target market -- worth
    confirming with the user which provider to actually configure once
    real WhatsApp credentials are in hand, since neither is a clear default
    picked in the plan beyond "one of these two."
    """

    def __init__(self) -> None:
        if not settings.zapi_instance_id or not settings.zapi_token:
            raise RuntimeError("ZAPI_INSTANCE_ID / ZAPI_TOKEN not configured")
        self._base_url = f"https://api.z-api.io/instances/{settings.zapi_instance_id}/token/{settings.zapi_token}"

    async def send_text(self, *, to_phone: str, message: str, correlation_id: str) -> ProviderSendResult:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{self._base_url}/send-text", json={"phone": to_phone, "message": message})
            response.raise_for_status()
            data = response.json()
        return ProviderSendResult(provider_message_id=data.get("messageId") or data.get("zaapId"), raw_response=data)

    async def parse_inbound_webhook(self, payload: dict) -> InboundMessage | None:
        # Z-API's inbound webhook shape (on-message-received): top-level
        # "phone" and "text": {"message": "..."}.
        from_phone = payload.get("phone")
        body = (payload.get("text") or {}).get("message")
        if not from_phone or not body:
            return None
        return InboundMessage(from_phone=from_phone, body=body, reference_code=None)
