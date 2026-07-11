import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.payment import CreateDepositChargeRequest, PaymentRecordResponse
from app.services import payment_service

router = APIRouter()

_ANY_ROLE = require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE)


@router.post("/appointments/{appointment_id}/deposit", response_model=PaymentRecordResponse, status_code=201)
async def create_deposit_charge(
    appointment_id: uuid.UUID,
    body: CreateDepositChargeRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentRecordResponse:
    result = await payment_service.create_deposit_charge(
        db, current_user.tenant_id, appointment_id, method=body.method
    )
    return PaymentRecordResponse(
        id=result.record.id,
        appointment_id=result.record.appointment_id,
        provider=result.record.provider,
        amount=result.record.amount,
        type=result.record.type,
        method=result.record.method,
        status=result.record.status,
        paid_at=result.record.paid_at,
        pix_qr_code=result.pix_qr_code,
        checkout_url=result.checkout_url,
    )


@router.post("/payments/{payment_record_id}/refresh", response_model=PaymentRecordResponse)
async def refresh_payment_status(
    payment_record_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> PaymentRecordResponse:
    """Polls the provider directly instead of waiting for a webhook -- see
    payment_service.refresh_payment_status's docstring for why this exists
    (a real webhook can't reach a server without a public URL, which local
    sandbox testing doesn't have).
    """
    record = await payment_service.refresh_payment_status(db, current_user.tenant_id, payment_record_id)
    return PaymentRecordResponse(
        id=record.id,
        appointment_id=record.appointment_id,
        provider=record.provider,
        amount=record.amount,
        type=record.type,
        method=record.method,
        status=record.status,
        paid_at=record.paid_at,
    )
