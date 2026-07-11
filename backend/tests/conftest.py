import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.database import set_tenant_context

settings = get_settings()


@pytest_asyncio.fixture
async def db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Real Postgres connection (app_runtime role -- the same restricted role
    the app uses, so RLS is genuinely exercised, not bypassed). Wrapped in a
    transaction that's always rolled back: tests never persist anything into
    the shared dev database, so no separate test database is needed.
    """
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            yield conn
        finally:
            await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    """ORM session joined onto the same rolled-back-at-the-end transaction as
    db_connection. session.commit() internally uses a SAVEPOINT (see
    join_transaction_mode) so the outer transaction -- and therefore the
    rollback -- stays intact regardless of what test code commits.
    """
    session = AsyncSession(bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def make_tenant(
    db_connection: AsyncConnection,
) -> Callable[..., Awaitable[uuid.UUID]]:
    """Insert a Company row directly (no service/repository layer needed for
    this) and set it as the active RLS tenant context for the rest of the
    test. Call again with a different slug to simulate a second tenant and
    switch context to it (SET LOCAL is overwritable within the same
    transaction, matching how the app switches context per-request).
    """

    async def _make_tenant(slug: str = "test-co", name: str | None = None) -> uuid.UUID:
        tenant_id = uuid.uuid4()
        await db_connection.execute(
            text("INSERT INTO companies (id, slug, name) VALUES (:id, :slug, :name)"),
            {"id": tenant_id, "slug": slug, "name": name or slug},
        )
        await set_tenant_context(db_connection, tenant_id)
        return tenant_id

    return _make_tenant


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
