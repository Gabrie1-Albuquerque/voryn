from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

PaymentMethodLiteral = Literal["pix", "credit_card"]


@dataclass(frozen=True)
class ChargeResult:
    provider_reference_id: str
    status: Literal["pending", "approved", "rejected"]
    # PIX: a copy-paste "QR code" payload (technically a BR Code / EMV
    # string) the client's bank app scans or pastes -- not an image, the
    # frontend renders it as a QR itself. Card: a checkout URL to redirect
    # to. Only one of these is populated, depending on method.
    pix_qr_code: str | None = None
    checkout_url: str | None = None


@dataclass(frozen=True)
class WebhookEvent:
    provider_reference_id: str
    status: Literal["pending", "approved", "rejected"]
    external_reference: str | None


class PaymentProvider(ABC):
    @abstractmethod
    async def create_charge(
        self,
        *,
        amount: Decimal,
        method: PaymentMethodLiteral,
        external_reference: str,
        description: str,
    ) -> ChargeResult: ...

    @abstractmethod
    async def get_charge_status(self, provider_reference_id: str) -> ChargeResult: ...

    @abstractmethod
    async def parse_webhook(self, payload: dict, headers: dict) -> WebhookEvent | None: ...
