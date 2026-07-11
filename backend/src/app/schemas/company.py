import uuid

from pydantic import BaseModel


class CompanyResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    document: str | None
    timezone: str
    plan_tier: str
    auto_confirm_public_bookings: bool


class CompanyUpdateRequest(BaseModel):
    name: str | None = None
    document: str | None = None
    timezone: str | None = None
    auto_confirm_public_bookings: bool | None = None
