import os
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine

# Must happen before the app.core.config import below: Settings.
# smtp_credentials_encryption_key's class-level default is deliberately an
# invalid, non-functional placeholder (unlike jwt_secret_key's, which is a
# working-but-insecure value) -- a real Fernet key is required or
# encrypt_secret/decrypt_secret raise. Generating one fresh per test session
# means tests never depend on any committed value, hardcoded or otherwise.
os.environ.setdefault("SMTP_CREDENTIALS_ENCRYPTION_KEY", Fernet.generate_key().decode())

from app.core.config import get_settings  # noqa: E402
from app.core.database import set_tenant_context  # noqa: E402

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


@pytest_asyncio.fixture
async def real_session_factory():
    """Opens a fresh, tenant-scoped session against a REAL engine (own
    connection pool, disposed at teardown) -- the real-commit counterpart to
    db_session, and the real-commit equivalent of what get_tenant_db/
    get_tenant_db_by_slug hand each request in the actual app. Callers open
    one of these per logical "request" being simulated, same as the real app
    would.

    Needs its own engine rather than reusing app.core.database's
    module-level one: that engine's pool persists across test functions,
    but pytest-asyncio gives each test function its own event loop by
    default, and asyncpg connections are bound to the loop they were
    created on -- reusing a pooled connection from a different test's loop
    crashes with "Future attached to a different loop". db_connection
    (above) sidesteps this the same way, with its own fresh engine per test.
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def _open(tenant_id: uuid.UUID) -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            await set_tenant_context(session, tenant_id)
            yield session

    try:
        yield _open
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def real_tenant(real_session_factory) -> AsyncGenerator[uuid.UUID, None]:
    """Unlike make_tenant, this commits for real -- required for any test
    that exercises commit/transaction-boundary behavior (e.g.
    set_tenant_context's SET LOCAL surviving -- or not -- across more than
    one commit within a session). db_session's session.commit() is secretly
    just a SAVEPOINT release (join_transaction_mode="create_savepoint"), so
    it can never revert a transaction-local set_config the way a real COMMIT
    does; tests built on it would stay green even if this exact class of bug
    came back. No rollback safety net here once a real commit has happened,
    so cleanup is explicit (deleting the Company CASCADEs to every
    tenant-owned row).
    """
    tenant_id = uuid.uuid4()
    async with real_session_factory(tenant_id) as session:
        await session.execute(
            text("INSERT INTO companies (id, slug, name) VALUES (:id, :slug, :name)"),
            {"id": tenant_id, "slug": f"real-{tenant_id.hex[:8]}", "name": "Real Commit Test Co"},
        )
        await session.commit()
    try:
        yield tenant_id
    finally:
        async with real_session_factory(tenant_id) as session:
            await session.execute(text("DELETE FROM companies WHERE id = :id"), {"id": tenant_id})
            await session.commit()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
