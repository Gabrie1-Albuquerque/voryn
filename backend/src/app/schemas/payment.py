import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PaymentMethod, PaymentProviderName, PaymentStatus, PaymentType
from app.providers.payments.base import PaymentMethodLiteral


class CreateDepositChargeRequest(BaseModel):
    method: PaymentMethodLiteral = "pix"


class PaymentRecordResponse(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    provider: PaymentProviderName
    amount: Decimal
    type: PaymentType
    method: PaymentMethod
    status: PaymentStatus
    paid_at: datetime | None
    pix_qr_code: str | None = None
    checkout_url: str | None = None
