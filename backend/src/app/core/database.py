import uuid
from collections.abc import AsyncGenerator
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

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
    """Plain, tenant-agnostic session dependency. Routes that need tenant
    scoping should depend on `get_tenant_db` (core/deps.py) instead, which
    layers `set_tenant_context` on top of this after resolving the tenant
    from the request (JWT for authenticated routes, slug for public ones).
    """
    async with async_session_factory() as session:
        yield session
