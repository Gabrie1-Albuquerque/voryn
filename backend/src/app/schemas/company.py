import uuid

from pydantic import BaseModel, Field, model_validator


class CompanyResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    document: str | None
    timezone: str
    plan_tier: str
    auto_confirm_public_bookings: bool
    reminder_first_hours: int
    reminder_second_hours: int


class CompanyUpdateRequest(BaseModel):
    name: str | None = None
    document: str | None = None
    timezone: str | None = None
    auto_confirm_public_bookings: bool | None = None
    reminder_first_hours: int | None = Field(default=None, gt=0, le=168)
    reminder_second_hours: int | None = Field(default=None, gt=0, le=168)

    @model_validator(mode="after")
    def _check_reminder_order(self) -> "CompanyUpdateRequest":
        # Mirrors ck_company_reminder_hours_order in the DB (belt-and-
        # suspenders like the rest of this codebase's constraints) -- but
        # only when BOTH are given together, since a lone field update is
        # validated against the other's existing DB value instead.
        if (
            self.reminder_first_hours is not None
            and self.reminder_second_hours is not None
            and self.reminder_first_hours <= self.reminder_second_hours
        ):
            raise ValueError("reminder_first_hours must be greater than reminder_second_hours")
        return self
