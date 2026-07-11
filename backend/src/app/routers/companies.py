from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.company import CompanyResponse, CompanyUpdateRequest
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
