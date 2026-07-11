import logging
import uuid

from app.providers.notifications.base import InboundMessage, NotificationProvider, ProviderSendResult

logger = logging.getLogger("app.notifications")


class ConsoleNotificationProvider(NotificationProvider):
    """Local-dev default: logs instead of sending over WhatsApp, so the whole
    reminder/confirmation/waitlist flow is exercisable end-to-end with zero
    external credentials (WhatsApp Business API approval is an external,
    human-review process outside this build's control -- see
    whatsapp_cloud_provider.py / zapi_provider.py for the real-provider code,
    which is complete but necessarily untested against a live account).
    """

    async def send_text(self, *, to_phone: str, message: str, correlation_id: str) -> ProviderSendResult:
        logger.info("WHATSAPP to=%s correlation_id=%s\n%s", to_phone, correlation_id, message)
        return ProviderSendResult(provider_message_id=f"console-{uuid.uuid4()}")

    async def parse_inbound_webhook(self, payload: dict) -> InboundMessage | None:
        # Local dev has no real inbound webhook traffic; present for
        # interface completeness and so tests can exercise the parsing shape.
        from_phone = payload.get("from_phone")
        body = payload.get("body")
        if not from_phone or not body:
            return None
        return InboundMessage(from_phone=from_phone, body=body, reference_code=payload.get("reference_code"))
