import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_secret
from app.core.exceptions import NotFoundError
from app.models.tenant import Company
from app.providers.email.base import SmtpConfig
from app.providers.email.smtp_provider import test_connection as _test_smtp_connection
from app.schemas.company import CompanyUpdateRequest, SmtpTestRequest


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
    payload = data.model_dump(exclude_unset=True)
    # smtp_password is write-only (schemas/company.py) and has no matching
    # column -- the generic setattr loop below would fail on it, so encrypt
    # it into smtp_password_encrypted and pop it out first.
    if "smtp_password" in payload:
        company.smtp_password_encrypted = encrypt_secret(payload.pop("smtp_password"))
    for field, value in payload.items():
        setattr(company, field, value)
    await session.commit()
    return company


async def test_smtp_connection(data: SmtpTestRequest) -> tuple[bool, str]:
    """Tests candidate SMTP credentials without persisting them -- see
    routers/companies.py's POST /me/test-smtp.
    """
    return await _test_smtp_connection(
        SmtpConfig(
            host=data.smtp_host,
            port=data.smtp_port,
            username=data.smtp_username,
            password=data.smtp_password,
            from_email=data.smtp_from_email,
        )
    )
