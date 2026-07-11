import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.catalog import RoomCreateRequest, RoomResponse, RoomUpdateRequest
from app.services import catalog_service

router = APIRouter()

_MANAGE = require_role(UserRole.ADMIN, UserRole.MANAGER)


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    current_user: CurrentUser = Depends(_MANAGE), db: AsyncSession = Depends(get_tenant_db)
) -> list[RoomResponse]:
    rooms = await catalog_service.list_rooms(db, current_user.tenant_id)
    return [RoomResponse.model_validate(r, from_attributes=True) for r in rooms]


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    body: RoomCreateRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> RoomResponse:
    room = await catalog_service.create_room(db, current_user.tenant_id, body)
    return RoomResponse.model_validate(room, from_attributes=True)


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: uuid.UUID,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> RoomResponse:
    room = await catalog_service.get_room(db, current_user.tenant_id, room_id)
    return RoomResponse.model_validate(room, from_attributes=True)


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: uuid.UUID,
    body: RoomUpdateRequest,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> RoomResponse:
    room = await catalog_service.update_room(db, current_user.tenant_id, room_id, body)
    return RoomResponse.model_validate(room, from_attributes=True)


@router.delete("/{room_id}", status_code=204)
async def deactivate_room(
    room_id: uuid.UUID,
    current_user: CurrentUser = Depends(_MANAGE),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    await catalog_service.deactivate_room(db, current_user.tenant_id, room_id)
