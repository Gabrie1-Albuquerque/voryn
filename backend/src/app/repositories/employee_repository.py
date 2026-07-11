import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.tenant import Employee
from app.repositories.base import TenantScopedRepository


class EmployeeRepository(TenantScopedRepository[Employee]):
    model = Employee

    def _with_relations(self):
        # populate_existing=True: without it, re-querying an Employee that's
        # already in the session's identity map (e.g. right after creating
        # it, or after replacing its availability/services) returns the
        # SAME Python object with its already-loaded collections left as-is
        # -- selectinload does not overwrite an attribute SQLAlchemy already
        # considers loaded, even if the underlying rows changed since. Safe
        # to force here because every caller flushes before re-fetching, so
        # there's never unflushed local state this could clobber.
        return select(Employee).options(
            selectinload(Employee.availability), selectinload(Employee.services)
        ).execution_options(populate_existing=True)

    async def get_with_relations(self, id: uuid.UUID) -> Employee | None:
        stmt = self._with_relations().where(Employee.id == id, Employee.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_relations(self) -> list[Employee]:
        stmt = self._with_relations().where(Employee.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
