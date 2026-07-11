import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import AppointmentStatus, DepositType, PaymentStatus
from app.providers.payments.base import PaymentMethodLiteral


class PublicCompanyResponse(BaseModel):
    name: str
    slug: str
    timezone: str


class PublicServiceResponse(BaseModel):
    id: uuid.UUID
    name: str
    duration_minutes: int
    price: Decimal
    deposit_required: bool
    deposit_type: DepositType | None
    deposit_value: Decimal | None


class PublicEmployeeResponse(BaseModel):
    id: uuid.UUID
    name: str
    service_ids: list[uuid.UUID]


class AvailabilityResponse(BaseModel):
    slots: list[datetime]


class PublicBookingCreateRequest(BaseModel):
    service_id: uuid.UUID
    employee_id: uuid.UUID
    starts_at: datetime
    client_name: str = Field(min_length=1)
    client_phone: str = Field(min_length=1)
    client_email: str | None = None
    notes: str | None = None
    payment_method: PaymentMethodLiteral = "pix"


class PublicBookingResponse(BaseModel):
    id: uuid.UUID
    status: AppointmentStatus
    starts_at: datetime
    ends_at: datetime
    service_name: str
    employee_name: str
    deposit_required: bool
    deposit_amount: Decimal | None
    payment_status: PaymentStatus | None
    pix_qr_code: str | None
    checkout_url: str | None
