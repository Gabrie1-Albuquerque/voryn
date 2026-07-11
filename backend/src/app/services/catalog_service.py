import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.catalog import Room, Service
from app.repositories.catalog_repository import RoomRepository, ServiceRepository
from app.schemas.catalog import (
    RoomCreateRequest,
    RoomUpdateRequest,
    ServiceCreateRequest,
    ServiceUpdateRequest,
)


async def list_services(session: AsyncSession, tenant_id: uuid.UUID) -> list[Service]:
    return await ServiceRepository(session, tenant_id).list()


async def get_service(session: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Service:
    service = await ServiceRepository(session, tenant_id).get(service_id)
    if service is None:
        raise NotFoundError("service not found")
    return service


async def create_service(session: AsyncSession, tenant_id: uuid.UUID, data: ServiceCreateRequest) -> Service:
    service = ServiceRepository(session, tenant_id).add(Service(**data.model_dump()))
    await session.commit()
    return service


async def update_service(
    session: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID, data: ServiceUpdateRequest
) -> Service:
    service = await get_service(session, tenant_id, service_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    if service.deposit_required and (service.deposit_type is None or service.deposit_value is None):
        raise ValidationError("deposit_type and deposit_value are required when deposit_required is true")
    await session.commit()
    return service


async def deactivate_service(session: AsyncSession, tenant_id: uuid.UUID, service_id: uuid.UUID) -> None:
    service = await get_service(session, tenant_id, service_id)
    service.is_active = False
    await session.commit()


async def list_rooms(session: AsyncSession, tenant_id: uuid.UUID) -> list[Room]:
    return await RoomRepository(session, tenant_id).list()


async def get_room(session: AsyncSession, tenant_id: uuid.UUID, room_id: uuid.UUID) -> Room:
    room = await RoomRepository(session, tenant_id).get(room_id)
    if room is None:
        raise NotFoundError("room not found")
    return room


async def create_room(session: AsyncSession, tenant_id: uuid.UUID, data: RoomCreateRequest) -> Room:
    room = RoomRepository(session, tenant_id).add(Room(**data.model_dump()))
    await session.commit()
    return room


async def update_room(
    session: AsyncSession, tenant_id: uuid.UUID, room_id: uuid.UUID, data: RoomUpdateRequest
) -> Room:
    room = await get_room(session, tenant_id, room_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    await session.commit()
    return room


async def deactivate_room(session: AsyncSession, tenant_id: uuid.UUID, room_id: uuid.UUID) -> None:
    room = await get_room(session, tenant_id, room_id)
    room.is_active = False
    await session.commit()
