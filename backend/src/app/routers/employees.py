import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.employee import (
    EmployeeCreateRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
    ReplaceAvailabilityRequest,
    ReplaceServicesRequest,
)
from app.services import employee_service

router = APIRouter()

_MANAGE = require_role(UserRole.ADMIN, UserRole.MANAGER)


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(
    current_user: CurrentUser = Depends(_MANAGE), db: AsyncSession = Depends(get_tenant_db)
) -> list[EmployeeResponse]:
    employees = await employee_service.list_employees(db, current_user.tenant_id)
    return [EmployeeResponse.from_model(e) for e in employees]


@router.post("", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    body: EmployeeCreateRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmployeeResponse:
    employee = await employee_service.create_employee(db, current_user.tenant_id, body)
    return EmployeeResponse.from_model(employee)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: uuid.UUID,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmployeeResponse:
    employee = await employee_service.get_employee(db, current_user.tenant_id, employee_id)
    return EmployeeResponse.from_model(employee)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: uuid.UUID,
    body: EmployeeUpdateRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmployeeResponse:
    employee = await employee_service.update_employee(db, current_user.tenant_id, employee_id, body)
    return EmployeeResponse.from_model(employee)


@router.delete("/{employee_id}", status_code=204)
async def deactivate_employee(
    employee_id: uuid.UUID,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    await employee_service.deactivate_employee(db, current_user.tenant_id, employee_id)


@router.put("/{employee_id}/services", response_model=EmployeeResponse)
async def replace_employee_services(
    employee_id: uuid.UUID,
    body: ReplaceServicesRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmployeeResponse:
    employee = await employee_service.replace_employee_services(
        db, current_user.tenant_id, employee_id, body.service_ids
    )
    return EmployeeResponse.from_model(employee)


@router.put("/{employee_id}/availability", response_model=EmployeeResponse)
async def replace_employee_availability(
    employee_id: uuid.UUID,
    body: ReplaceAvailabilityRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> EmployeeResponse:
    employee = await employee_service.replace_employee_availability(
        db, current_user.tenant_id, employee_id, body.windows
    )
    return EmployeeResponse.from_model(employee)
