from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.company import (
    CompanyResponse,
    CompanyUpdateRequest,
    MercadoPagoTestRequest,
    MercadoPagoTestResponse,
    SmtpTestRequest,
    SmtpTestResponse,
    WhatsAppConnectResponse,
    WhatsAppStatusResponse,
)
from app.services import company_service

router = APIRouter()


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_tenant_db),
) -> CompanyResponse:
    company = await company_service.get_company(db, current_user.tenant_id)
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.patch("/me", response_model=CompanyResponse)
async def update_my_company(
    body: CompanyUpdateRequest,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_tenant_db),
) -> CompanyResponse:
    company = await company_service.update_company(db, current_user.tenant_id, body)
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.post("/me/test-smtp", response_model=SmtpTestResponse)
async def test_my_smtp_connection(
    body: SmtpTestRequest,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
) -> SmtpTestResponse:
    # No DB session needed -- tests the candidate credentials in the request
    # body directly, without persisting anything (see company_service.py).
    success, message = await company_service.test_smtp_connection(body)
    return SmtpTestResponse(success=success, message=message)


@router.post("/me/test-mercadopago", response_model=MercadoPagoTestResponse)
async def test_my_mercadopago_token(
    body: MercadoPagoTestRequest,
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
) -> MercadoPagoTestResponse:
    success, message = await company_service.test_mercadopago_token(body)
    return MercadoPagoTestResponse(success=success, message=message)


@router.post("/me/whatsapp/connect", response_model=WhatsAppConnectResponse)
async def connect_my_whatsapp(
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_tenant_db),
) -> WhatsAppConnectResponse:
    """Proxies Evolution API so its key never leaves the backend: creates
    this tenant's instance if needed and returns the QR code for the admin
    to scan with the business's own WhatsApp (Aparelhos conectados).
    """
    state, qr = await company_service.connect_whatsapp(db, current_user.tenant_id)
    return WhatsAppConnectResponse(state=state, qr_base64=qr)


@router.get("/me/whatsapp/status", response_model=WhatsAppStatusResponse)
async def my_whatsapp_status(
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_tenant_db),
) -> WhatsAppStatusResponse:
    state = await company_service.whatsapp_status(db, current_user.tenant_id)
    return WhatsAppStatusResponse(state=state)
