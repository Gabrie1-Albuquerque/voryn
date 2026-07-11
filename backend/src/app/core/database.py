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
    """One session per request. Resolves the tenant straight from the JWT (no
    DB round-trip needed, unlike login itself) and sets RLS context before
    any route code can run a query.

    Does NOT commit after yield -- an earlier version did, on the theory
    that a single commit point here would stop service code from committing
    mid-request and losing RLS context on a subsequent query (a real bug,
    see set_tenant_context's docstring history). That theory was correct but
    the mechanism was wrong: FastAPI/Starlette runs a yield-dependency's
    post-yield code AFTER the response has already been sent to the client,
    not before. Confirmed by reproducing it directly: POST an employee, then
    immediately GET it back with no delay, and it 404s -- the client
    receives "201 Created" before the INSERT's transaction actually commits.
    Waiting ~1s made it consistently visible, i.e. this was never "usually
    fine", it was a real, always-present race, just one easy to not notice
    by hand.

    The actual fix: every service function that writes calls
    session.commit() itself, as its last line, after any re-fetch-with-
    relations it needs (which must happen via flush(), before that commit,
    to keep RLS context for it) -- see e.g. employee_service.create_employee
    for the shape. That makes the commit part of the route handler's own
    synchronous execution, which necessarily finishes before FastAPI builds
    the response at all. This dependency's job is now just providing a
    correctly tenant-scoped session and, on an exception, doing nothing --
    the `async with` block's own cleanup rolls back automatically since
    nothing here commits.
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
