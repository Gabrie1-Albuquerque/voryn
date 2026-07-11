import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, set_tenant_context
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.models.enums import UserRole

# tokenUrl is only used to populate OpenAPI's "Authorize" button (path as
# FastAPI itself sees it, without the /api prefix nginx strips before
# proxying here); the actual login endpoint is JSON, not form-encoded,
# unlike the OAuth2 password flow this class is nominally modeling.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: UserRole


async def get_tenant_db(
    token: str | None = Depends(oauth2_scheme),
) -> AsyncGenerator[AsyncSession, None]:
    """One session per request. Resolves the tenant straight from the JWT
    (no DB round-trip needed, unlike login itself) and sets RLS context
    before any route code can run a query -- so every authenticated route
    gets tenant-scoped queries for free just by depending on this.
    """
    if token is None:
        raise AuthenticationError("missing bearer token")
    try:
        claims = decode_token(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("invalid or expired token") from exc
    if claims.get("type") != "access":
        raise AuthenticationError("not an access token")

    tenant_id = uuid.UUID(claims["tenant_id"])
    async with async_session_factory() as session:
        await set_tenant_context(session, tenant_id)
        yield session


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
) -> CurrentUser:
    """Cheap, DB-free claim extraction for authorization checks
    (require_role). Route handlers that need the full User row should fetch
    it themselves via UserRepository(db, current_user.tenant_id) -- kept
    separate so authorization doesn't force a query on every request.
    """
    if token is None:
        raise AuthenticationError("missing bearer token")
    try:
        claims = decode_token(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("invalid or expired token") from exc
    if claims.get("type") != "access":
        raise AuthenticationError("not an access token")

    return CurrentUser(
        user_id=uuid.UUID(claims["sub"]),
        tenant_id=uuid.UUID(claims["tenant_id"]),
        role=UserRole(claims["role"]),
    )


def require_role(*allowed_roles: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    """Dependency factory: Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)).

    Kept as a wrapper around get_current_user (rather than a class with
    __call__) so each call site gets its own FastAPI-cached dependency
    instance keyed by the specific roles passed in.
    """

    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError(f"role {current_user.role.value!r} cannot perform this action")
        return current_user

    return _check
