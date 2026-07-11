from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSendResult:
    provider_message_id: str | None
    raw_response: dict | None = None


@dataclass(frozen=True)
class InboundMessage:
    """A normalized inbound reply, regardless of which provider parsed it."""

    from_phone: str
    body: str
    reference_code: str | None  # see zapi_provider.py's note on why this matters more than phone matching


class NotificationProvider(ABC):
    @abstractmethod
    async def send_text(self, *, to_phone: str, message: str, correlation_id: str) -> ProviderSendResult: ...

    @abstractmethod
    async def parse_inbound_webhook(self, payload: dict) -> InboundMessage | None: ...
