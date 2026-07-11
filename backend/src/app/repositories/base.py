import uuid
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    """Base for every repository touching a tenant-owned table.

    Requires tenant_id at construction and filters every query on it --
    structurally impossible to query a tenant table without the filter from
    this layer. Postgres RLS (core/database.py:set_tenant_context) is the
    defense-in-depth backstop behind this, not a substitute for it.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def get(self, id: uuid.UUID) -> ModelT | None:
        stmt = select(self.model).where(self.model.id == id, self.model.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, **equality_filters: object) -> list[ModelT]:
        stmt = select(self.model).where(self.model.tenant_id == self.tenant_id)
        for column_name, value in equality_filters.items():
            stmt = stmt.where(getattr(self.model, column_name) == value)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add(self, instance: ModelT) -> ModelT:
        instance.tenant_id = self.tenant_id
        self.session.add(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
