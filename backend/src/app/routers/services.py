import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.catalog import ServiceCreateRequest, ServiceResponse, ServiceUpdateRequest
from app.services import catalog_service

router = APIRouter()

_MANAGE = require_role(UserRole.ADMIN, UserRole.MANAGER)


@router.get("", response_model=list[ServiceResponse])
async def list_services(
    current_user: CurrentUser = Depends(_MANAGE), db: AsyncSession = Depends(get_tenant_db)
) -> list[ServiceResponse]:
    services = await catalog_service.list_services(db, current_user.tenant_id)
    return [ServiceResponse.model_validate(s, from_attributes=True) for s in services]


@router.post("", response_model=ServiceResponse, status_code=201)
async def create_service(
    body: ServiceCreateRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ServiceResponse:
    service = await catalog_service.create_service(db, current_user.tenant_id, body)
    return ServiceResponse.model_validate(service, from_attributes=True)


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: uuid.UUID,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ServiceResponse:
    service = await catalog_service.get_service(db, current_user.tenant_id, service_id)
    return ServiceResponse.model_validate(service, from_attributes=True)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: uuid.UUID,
    body: ServiceUpdateRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ServiceResponse:
    service = await catalog_service.update_service(db, current_user.tenant_id, service_id, body)
    return ServiceResponse.model_validate(service, from_attributes=True)


@router.delete("/{service_id}", status_code=204)
async def deactivate_service(
    service_id: uuid.UUID,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    await catalog_service.deactivate_service(db, current_user.tenant_id, service_id)
