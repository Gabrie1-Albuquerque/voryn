import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.core.exceptions import PermissionDeniedError
from app.models.appointment import Appointment
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.appointment import AppointmentCreateRequest, AppointmentRescheduleRequest, AppointmentResponse
from app.services import appointment_service

router = APIRouter()

_ANY_ROLE = require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE)


async def _employee_scope(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID | None:
    """None means "no restriction" (ADMIN/MANAGER see everyone's agenda).
    Funcionário is scoped to their own agenda per the plan's RBAC shape --
    returning their linked employee_id enforces that in every list/action
    below. An EMPLOYEE-role user with no linked Employee record has nothing
    to be scoped to, so this raises rather than silently falling through to
    "no restriction" (which would hand them the whole company's agenda).
    """
    if current_user.role != UserRole.EMPLOYEE:
        return None
    user = await UserRepository(db, current_user.tenant_id).get(current_user.user_id)
    if user is None or user.employee_id is None:
        raise PermissionDeniedError("this account is not linked to an employee record")
    return user.employee_id


def _assert_in_scope(employee_id: uuid.UUID, scope: uuid.UUID | None) -> None:
    if scope is not None and employee_id != scope:
        raise PermissionDeniedError("cannot access another employee's appointments")


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    start: datetime = Query(...),
    end: datetime = Query(...),
    employee_id: uuid.UUID | None = Query(default=None),
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[AppointmentResponse]:
    scope = await _employee_scope(current_user, db)
    if employee_id is not None:
        _assert_in_scope(employee_id, scope)
    effective_employee_id = employee_id or scope
    appointments = await appointment_service.list_appointments(
        db, current_user.tenant_id, start=start, end=end, employee_id=effective_employee_id
    )
    return [AppointmentResponse.from_model(a) for a in appointments]


@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    body: AppointmentCreateRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    scope = await _employee_scope(current_user, db)
    _assert_in_scope(body.employee_id, scope)
    appointment = await appointment_service.create_appointment(
        db,
        current_user.tenant_id,
        client_id=body.client_id,
        employee_id=body.employee_id,
        service_id=body.service_id,
        room_id=body.room_id,
        starts_at=body.starts_at,
        notes=body.notes,
        created_by_user_id=current_user.user_id,
    )
    return AppointmentResponse.from_model(appointment)


async def _get_in_scope(
    appointment_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession
) -> tuple[Appointment, uuid.UUID | None]:
    scope = await _employee_scope(current_user, db)
    appointment = await appointment_service.get_appointment(db, current_user.tenant_id, appointment_id)
    _assert_in_scope(appointment.employee_id, scope)
    return appointment, scope


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    appointment, _ = await _get_in_scope(appointment_id, current_user, db)
    return AppointmentResponse.from_model(appointment)


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    await _get_in_scope(appointment_id, current_user, db)
    appointment = await appointment_service.confirm_appointment(
        db, current_user.tenant_id, appointment_id, changed_by=str(current_user.user_id)
    )
    return AppointmentResponse.from_model(appointment)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    await _get_in_scope(appointment_id, current_user, db)
    appointment = await appointment_service.cancel_appointment(
        db, current_user.tenant_id, appointment_id, changed_by=str(current_user.user_id)
    )
    return AppointmentResponse.from_model(appointment)


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    await _get_in_scope(appointment_id, current_user, db)
    appointment = await appointment_service.complete_appointment(
        db, current_user.tenant_id, appointment_id, changed_by=str(current_user.user_id)
    )
    return AppointmentResponse.from_model(appointment)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentRescheduleRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> AppointmentResponse:
    await _get_in_scope(appointment_id, current_user, db)
    appointment = await appointment_service.reschedule_appointment(
        db,
        current_user.tenant_id,
        appointment_id,
        new_starts_at=body.new_starts_at,
        changed_by=str(current_user.user_id),
    )
    return AppointmentResponse.from_model(appointment)
