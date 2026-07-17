import httpx

from app.core.config import get_settings
from app.providers.notifications.base import InboundMessage, NotificationProvider, ProviderSendResult

settings = get_settings()

GRAPH_API_VERSION = "v20.0"


class WhatsAppCloudProvider(NotificationProvider):
    """Meta's official WhatsApp Cloud API. Correct request shape and auth,
    but cannot be tested against a live account within this build: Meta
    Business verification and message-template approval are external,
    human-review processes that take days to weeks and are outside this
    session's control (unlike Mercado Pago, which offers self-service
    sandbox credentials -- see payments/mercadopago_provider.py).

    Business-initiated messages (which every reminder in this app is --
    the business is proactively contacting the customer, not replying
    within an active support conversation) MUST use a pre-approved message
    TEMPLATE, not free-form text -- Meta's API rejects a plain "text" type
    message outside a 24h customer-service window. `template_name` below is
    a placeholder; the real one only exists once a template is submitted
    and approved in the Meta Business account, so this can't be hardcoded
    correctly yet. Swap it (and the components/variable mapping) for the
    real approved template name once that account exists.
    """

    def __init__(self) -> None:
        if not settings.whatsapp_cloud_token or not settings.whatsapp_cloud_phone_number_id:
            raise RuntimeError("WHATSAPP_CLOUD_TOKEN / WHATSAPP_CLOUD_PHONE_NUMBER_ID not configured")
        self._token = settings.whatsapp_cloud_token
        self._phone_number_id = settings.whatsapp_cloud_phone_number_id
        self._base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{self._phone_number_id}/messages"

    async def send_text(
        self, *, to_phone: str, message: str, correlation_id: str, instance: str | None = None
    ) -> ProviderSendResult:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": "appointment_notification",  # placeholder -- see class docstring
                "language": {"code": "pt_BR"},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": message}]}],
            },
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self._base_url,
                headers={"Authorization": f"Bearer {self._token}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        message_id = data.get("messages", [{}])[0].get("id")
        return ProviderSendResult(provider_message_id=message_id, raw_response=data)

    async def parse_inbound_webhook(self, payload: dict) -> InboundMessage | None:
        # Meta's webhook shape: entry[].changes[].value.messages[]
        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]
            value = change["value"]
            message = value["messages"][0]
        except (KeyError, IndexError):
            return None

        from_phone = message.get("from")
        body = message.get("text", {}).get("body")
        if not from_phone or not body:
            return None
        # Meta doesn't give us a natural "reference code" field -- if outbound
        # reminders embed one in the message body/template variables, it'd
        # need to be extracted from context (e.g. the most recent
        # NotificationLog for this phone number) rather than from the
        # webhook payload itself.
        return InboundMessage(from_phone=from_phone, body=body, reference_code=None)
