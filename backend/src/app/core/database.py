import uuid
from collections.abc import AsyncGenerator
from typing import Protocol

import jwt
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import decode_token, oauth2_scheme

settings = get_settings()

engine: AsyncEngine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


class ExecutesSQL(Protocol):
    async def execute(self, statement, parameters=None): ...  # noqa: ANN001, ANN201


async def set_tenant_context(executor: ExecutesSQL, tenant_id: uuid.UUID) -> None:
    """Set the Postgres session variable Row-Level Security policies key off.

    Must run inside the same transaction as the queries it's meant to scope
    (SET LOCAL is transaction-scoped), so callers use this right after opening
    a session/connection and before issuing any tenant-scoped query. This is
    the defense-in-depth backstop behind repository-level tenant_id filtering
    -- see app/models/base.py:TenantMixin. Accepts anything with an
    AsyncSession-or-AsyncConnection-shaped `execute()` (both satisfy
    ExecutesSQL), since tests key off a raw connection while request handling
    keys off a session.

    Uses set_config(), not `SET LOCAL ... = :param`: SET is a utility
    statement in Postgres's grammar and doesn't accept bind parameters at
    all (asyncpg sends a `$1` placeholder that Postgres's parser rejects
    with a syntax error) -- set_config() is an ordinary function call, so it
    takes a real parameter. The third argument (true) makes it
    transaction-local, matching SET LOCAL's scope.
    """
    await executor.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"), {"tenant_id": str(tenant_id)}
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Plain, tenant-agnostic session dependency, for routes that run before
    a tenant is known at all (e.g. login itself). Routes that need tenant
    scoping should depend on `get_tenant_db` instead.
    """
    async with async_session_factory() as session:
        yield session


async def get_tenant_db(
    token: str | None = Depends(oauth2_scheme),
) -> AsyncGenerator[AsyncSession, None]:
    """One session per request, with exactly one commit point: right here,
    after the route handler returns successfully. Resolves the tenant
    straight from the JWT (no DB round-trip needed, unlike login itself) and
    sets RLS context before any route code can run a query.

    Services must use session.flush() (not commit()) when they need
    server-generated values (ids, defaults) populated mid-request --
    committing ends the transaction that the tenant's SET LOCAL context
    lives in, so anything that queries again afterwards (a refresh, a
    re-fetch-with-relations) hits Postgres with no tenant context set and
    RLS rejects it. This bit for real building CRUD endpoints: create/update
    handlers that committed then re-queried started failing with "invalid
    input syntax for type uuid: ''" (the RLS policy casting the now-empty
    GUC), and it was silent in tests because the test fixtures wrap
    everything in one outer transaction via savepoints, which never hits a
    real commit boundary. One commit per request, here, is what makes it
    impossible for service code to reintroduce this.

    If the route handler raises, this generator never reaches the commit
    line below (FastAPI throws the exception in at the yield point) and the
    `async with` block's own cleanup rolls back on exit, so no explicit
    except/rollback is needed here.
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
        await session.commit()
