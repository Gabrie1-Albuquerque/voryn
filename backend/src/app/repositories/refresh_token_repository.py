import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.auth import RefreshToken
from app.repositories.base import TenantScopedRepository


class RefreshTokenRepository(TenantScopedRepository[RefreshToken]):
    model = RefreshToken

    async def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.tenant_id == self.tenant_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = select(RefreshToken).where(
            RefreshToken.tenant_id == self.tenant_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        result = await self.session.execute(stmt)
        now = datetime.now(timezone.utc)
        for token in result.scalars().all():
            token.revoked_at = now
