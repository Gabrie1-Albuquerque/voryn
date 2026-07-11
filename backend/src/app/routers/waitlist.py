import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.waitlist import WaitlistEntryCreateRequest, WaitlistEntryResponse
from app.services import waitlist_service

router = APIRouter()

_ANY_ROLE = require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE)


@router.get("", response_model=list[WaitlistEntryResponse])
async def list_waitlist(
    current_user: CurrentUser = Depends(_ANY_ROLE), db: AsyncSession = Depends(get_tenant_db)
) -> list[WaitlistEntryResponse]:
    entries = await waitlist_service.list_waitlist(db, current_user.tenant_id)
    return [WaitlistEntryResponse.model_validate(e, from_attributes=True) for e in entries]


@router.post("", response_model=WaitlistEntryResponse, status_code=201)
async def join_waitlist(
    body: WaitlistEntryCreateRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> WaitlistEntryResponse:
    entry = await waitlist_service.join_waitlist(
        db,
        current_user.tenant_id,
        client_id=body.client_id,
        service_id=body.service_id,
        preferred_window_start=body.preferred_window_start,
        preferred_window_end=body.preferred_window_end,
        preferred_employee_id=body.preferred_employee_id,
    )
    return WaitlistEntryResponse.model_validate(entry, from_attributes=True)


@router.delete("/{entry_id}", status_code=204)
async def cancel_waitlist_entry(
    entry_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    await waitlist_service.cancel_waitlist_entry(db, current_user.tenant_id, entry_id)
