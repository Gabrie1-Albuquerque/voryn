from app.models.catalog import Room, Service
from app.repositories.base import TenantScopedRepository


class ServiceRepository(TenantScopedRepository[Service]):
    model = Service


class RoomRepository(TenantScopedRepository[Room]):
    model = Room
