import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.tenant import User
from app.repositories.base import TenantScopedRepository


class UserRepository(TenantScopedRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        # Still tenant-scoped: this is for "find a teammate in my own
        # company", not authentication (see find_login_credentials for that).
        stmt = select(User).where(User.email == email, User.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


@dataclass(frozen=True)
class LoginCredentials:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    password_hash: str
    role: UserRole
    is_active: bool


async def find_login_credentials(session: AsyncSession, email: str) -> LoginCredentials | None:
    """The one deliberate pre-tenant-context lookup in the system: calls the
    SECURITY DEFINER function from migration 0002, which bypasses RLS
    internally (running as its owner) so we can discover which tenant a
    login belongs to before set_tenant_context() can be called. Returns only
    the fields needed to authenticate, not a full User row.
    """
    result = await session.execute(text("SELECT * FROM find_login_credentials(:email)"), {"email": email})
    row = result.mappings().one_or_none()
    if row is None:
        return None
    return LoginCredentials(
        user_id=row["user_id"],
        tenant_id=row["tenant_id"],
        password_hash=row["password_hash"],
        role=UserRole(row["role"]),
        is_active=row["is_active"],
    )
