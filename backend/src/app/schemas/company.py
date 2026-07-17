import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator


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
    # Non-secret SMTP fields only -- smtp_password_encrypted never appears
    # here, on purpose (see Company.smtp_configured in models/tenant.py).
    smtp_host: str | None
    smtp_port: int | None
    smtp_username: str | None
    smtp_from_email: str | None
    smtp_configured: bool
    # Mercado Pago: only the derived boolean -- token/secret never appear,
    # not even partially.
    mercadopago_configured: bool


class CompanyUpdateRequest(BaseModel):
    name: str | None = None
    document: str | None = None
    timezone: str | None = None
    auto_confirm_public_bookings: bool | None = None
    reminder_first_hours: int | None = Field(default=None, gt=0, le=168)
    reminder_second_hours: int | None = Field(default=None, gt=0, le=168)
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, gt=0, le=65535)
    smtp_username: str | None = None
    # Write-only: omit to leave the already-saved password untouched (same
    # exclude_unset=True effect the rest of this schema already relies on).
    # Encrypted by company_service.update_company before it ever reaches the
    # Company model -- there is no plaintext "smtp_password" column.
    smtp_password: str | None = None
    smtp_from_email: EmailStr | None = None
    # Write-only, same pattern as smtp_password: encrypted into
    # mp_*_encrypted by company_service.update_company.
    mercadopago_access_token: str | None = None
    mercadopago_webhook_secret: str | None = None

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


class SmtpTestRequest(BaseModel):
    """Tests candidate credentials before they're ever persisted -- all
    fields required, unlike CompanyUpdateRequest's partial-patch shape,
    since a connection test only makes sense with a complete credential set.
    """

    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(gt=0, le=65535)
    smtp_username: str = Field(min_length=1)
    smtp_password: str = Field(min_length=1)
    smtp_from_email: EmailStr


class SmtpTestResponse(BaseModel):
    success: bool
    message: str


class MercadoPagoTestRequest(BaseModel):
    """Validates a candidate access token against Mercado Pago's own API
    before it's ever persisted -- same test-before-save shape as SmtpTestRequest.
    """

    access_token: str = Field(min_length=1)


class MercadoPagoTestResponse(BaseModel):
    success: bool
    message: str


class WhatsAppConnectResponse(BaseModel):
    """QR code for linking the business's own WhatsApp number to its
    Evolution instance -- base64 data-URI, rendered directly by the
    Settings screen. Absent when the instance is already connected.
    """

    state: str  # connecting | open | close
    qr_base64: str | None = None


class WhatsAppStatusResponse(BaseModel):
    state: str  # connecting | open | close | not_created
