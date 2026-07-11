import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.tenant import Company
from app.schemas.company import CompanyUpdateRequest


async def get_company(session: AsyncSession, tenant_id: uuid.UUID) -> Company:
    # Company IS the tenant (no tenant_id column of its own), so this is a
    # plain get-by-id, not a TenantScopedRepository -- there's no broader
    # "list all companies" operation for a tenant-scoped caller to abuse.
    company = await session.get(Company, tenant_id)
    if company is None:
        raise NotFoundError("company not found")
    return company


async def update_company(session: AsyncSession, tenant_id: uuid.UUID, data: CompanyUpdateRequest) -> Company:
    company = await get_company(session, tenant_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await session.flush()
    return company
