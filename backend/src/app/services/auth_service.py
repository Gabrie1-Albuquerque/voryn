import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import set_tenant_context
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    parse_refresh_token_tenant,
    verify_password,
    verify_password_reset_fingerprint,
)
from app.models.auth import RefreshToken
from app.models.enums import UserRole
from app.providers.email.factory import get_email_provider
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository, find_login_credentials

settings = get_settings()


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


async def _issue_token_pair(
    session: AsyncSession, *, user_id: uuid.UUID, tenant_id: uuid.UUID, role: UserRole
) -> TokenPair:
    access_token = create_access_token(user_id=user_id, tenant_id=tenant_id, role=role)
    raw_refresh, refresh_hash = generate_refresh_token(tenant_id)
    RefreshTokenRepository(session, tenant_id).add(
        RefreshToken(
            user_id=user_id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await session.commit()
    return TokenPair(access_token=access_token, refresh_token=raw_refresh)


async def login(session: AsyncSession, *, email: str, password: str) -> TokenPair:
    credentials = await find_login_credentials(session, email)
    # Same error for "no such user" and "wrong password": don't let a client
    # distinguish account existence from a wrong password.
    if credentials is None or not credentials.is_active:
        raise AuthenticationError("invalid email or password")
    if not verify_password(password, credentials.password_hash):
        raise AuthenticationError("invalid email or password")

    await set_tenant_context(session, credentials.tenant_id)
    return await _issue_token_pair(
        session, user_id=credentials.user_id, tenant_id=credentials.tenant_id, role=credentials.role
    )


async def refresh(session: AsyncSession, *, raw_refresh_token: str) -> TokenPair:
    try:
        tenant_id = parse_refresh_token_tenant(raw_refresh_token)
    except ValueError as exc:
        raise AuthenticationError("invalid refresh token") from exc

    await set_tenant_context(session, tenant_id)
    repo = RefreshTokenRepository(session, tenant_id)
    token_row = await repo.get_valid_by_hash(hash_refresh_token(raw_refresh_token))
    if token_row is None:
        raise AuthenticationError("invalid or expired refresh token")

    user = await UserRepository(session, tenant_id).get(token_row.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("invalid or expired refresh token")

    # Rotate: the old refresh token is single-use, so a stolen-then-replayed
    # token is detectable (the legitimate client's next refresh will fail).
    await repo.revoke(token_row)
    return await _issue_token_pair(session, user_id=user.id, tenant_id=tenant_id, role=user.role)


async def logout(session: AsyncSession, *, raw_refresh_token: str) -> None:
    try:
        tenant_id = parse_refresh_token_tenant(raw_refresh_token)
    except ValueError:
        return  # Already-invalid token: logout is a no-op, not an error.

    await set_tenant_context(session, tenant_id)
    repo = RefreshTokenRepository(session, tenant_id)
    token_row = await repo.get_valid_by_hash(hash_refresh_token(raw_refresh_token))
    if token_row is not None:
        await repo.revoke(token_row)
        await session.commit()


async def request_password_reset(session: AsyncSession, *, email: str) -> None:
    """Always returns normally, whether or not the email exists -- the caller
    (router) always responds with the same generic "check your email"
    message, so this can't be used to enumerate registered addresses.
    """
    credentials = await find_login_credentials(session, email)
    if credentials is None or not credentials.is_active:
        return

    reset_token = create_password_reset_token(
        user_id=credentials.user_id,
        tenant_id=credentials.tenant_id,
        current_password_hash=credentials.password_hash,
    )
    reset_link = f"{settings.public_app_url}/reset-password?token={reset_token}"
    await get_email_provider().send(
        to=email,
        subject="Redefinição de senha",
        body=f"Clique no link para redefinir sua senha (válido por 30 minutos): {reset_link}",
    )


async def reset_password(session: AsyncSession, *, token: str, new_password: str) -> None:
    try:
        claims = decode_password_reset_token(token)
    except Exception as exc:  # noqa: BLE001 - any decode/format failure -> generic invalid-link error
        raise AuthenticationError("invalid or expired reset link") from exc

    await set_tenant_context(session, claims.tenant_id)
    user = await UserRepository(session, claims.tenant_id).get(claims.user_id)
    if user is None:
        raise NotFoundError("user not found")

    try:
        verify_password_reset_fingerprint(token, current_password_hash=user.password_hash)
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError("invalid or expired reset link") from exc

    user.password_hash = hash_password(new_password)
    await RefreshTokenRepository(session, claims.tenant_id).revoke_all_for_user(claims.user_id)
    await session.commit()
