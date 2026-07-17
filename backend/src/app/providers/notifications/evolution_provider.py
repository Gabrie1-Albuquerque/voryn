import httpx

from app.core.config import get_settings
from app.providers.notifications.base import InboundMessage, NotificationProvider, ProviderSendResult

settings = get_settings()


class EvolutionApiProvider(NotificationProvider):
    """Self-hosted Evolution API (v2): one deployment, one INSTANCE per
    tenant -- each business connects its own WhatsApp number by scanning a
    QR code from the Settings screen (see routers/companies.py's
    /me/whatsapp/* proxy endpoints), so clients receive messages from the
    number they already know. Chosen over Z-API (~R$100/mo per number) and
    Meta's official Cloud API (weeks of business verification + template
    approval) for its fixed R$0/month cost -- explicit user decision.

    Every request shape below was verified empirically against a running
    Evolution v2.3.7 container, including the failure mode that matters
    most: sendText on a disconnected instance HANGS instead of erroring
    fast, so the timeout here is deliberately short and callers must treat
    a timeout as a failed send (notification_service already isolates
    per-channel failures into FAILED NotificationLog rows).
    """

    def __init__(self) -> None:
        if not settings.evolution_api_url or not settings.evolution_api_key:
            raise RuntimeError("EVOLUTION_API_URL / EVOLUTION_API_KEY not configured")
        self._base_url = settings.evolution_api_url.rstrip("/")
        self._headers = {"apikey": settings.evolution_api_key}

    async def send_text(
        self, *, to_phone: str, message: str, correlation_id: str, instance: str | None = None
    ) -> ProviderSendResult:
        if not instance:
            raise ValueError("EvolutionApiProvider.send_text() requires the tenant's instance name")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._base_url}/message/sendText/{instance}",
                headers=self._headers,
                json={"number": to_phone, "text": message},
            )
            response.raise_for_status()
            data = response.json()
        return ProviderSendResult(
            provider_message_id=(data.get("key") or {}).get("id"), raw_response=data
        )

    async def parse_inbound_webhook(self, payload: dict) -> InboundMessage | None:
        # Evolution's MESSAGES_UPSERT event: data.key.remoteJid holds the
        # sender as "5548...@s.whatsapp.net"; data.message.conversation holds
        # plain text (extendedTextMessage.text for replies/links). fromMe
        # events are the business's own outbound messages echoed back --
        # never actionable client replies.
        if payload.get("event") not in ("messages.upsert", "MESSAGES_UPSERT"):
            return None
        data = payload.get("data") or {}
        key = data.get("key") or {}
        if key.get("fromMe"):
            return None
        remote_jid = key.get("remoteJid") or ""
        from_phone = remote_jid.split("@", 1)[0]
        message = data.get("message") or {}
        body = message.get("conversation") or (message.get("extendedTextMessage") or {}).get("text")
        if not from_phone or not body:
            return None
        return InboundMessage(from_phone=from_phone, body=body, reference_code=None)
