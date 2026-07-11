import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_role
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.tenant import User
from app.services import auth_service


async def _seed_admin(session: AsyncSession, tenant_id: uuid.UUID, *, password: str = "senha-forte-123") -> User:
    user = User(
        tenant_id=tenant_id,
        email=f"{uuid.uuid4()}@example.com",
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_login_success(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id, password="senha-forte-123")

    tokens = await auth_service.login(db_session, email=user.email, password="senha-forte-123")
    assert tokens.access_token
    assert tokens.refresh_token.startswith(str(tenant_id))


@pytest.mark.asyncio
async def test_login_wrong_password_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id, password="senha-forte-123")

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, email=user.email, password="senha-errada")


@pytest.mark.asyncio
async def test_login_nonexistent_email_raises_same_error(db_session: AsyncSession, make_tenant):
    await make_tenant()

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, email="ninguem@example.com", password="qualquer")


@pytest.mark.asyncio
async def test_login_inactive_user_raises(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id, password="senha-forte-123")
    user.is_active = False
    await db_session.flush()

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, email=user.email, password="senha-forte-123")


@pytest.mark.asyncio
async def test_refresh_rotates_and_invalidates_old_token(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id)
    first = await auth_service.login(db_session, email=user.email, password="senha-forte-123")

    second = await auth_service.refresh(db_session, raw_refresh_token=first.refresh_token)
    assert second.refresh_token != first.refresh_token

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, raw_refresh_token=first.refresh_token)


@pytest.mark.asyncio
async def test_refresh_with_malformed_token_raises(db_session: AsyncSession, make_tenant):
    await make_tenant()

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, raw_refresh_token="not-a-valid-token-shape")


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id)
    tokens = await auth_service.login(db_session, email=user.email, password="senha-forte-123")

    await auth_service.logout(db_session, raw_refresh_token=tokens.refresh_token)

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, raw_refresh_token=tokens.refresh_token)


@pytest.mark.asyncio
async def test_password_reset_flow_end_to_end(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id, password="senha-antiga")

    # Sessions issued before the reset must not survive it.
    pre_reset_tokens = await auth_service.login(db_session, email=user.email, password="senha-antiga")

    sent: list[tuple[str, str]] = []

    class _CapturingEmailProvider:
        async def send(self, *, to: str, subject: str, body: str) -> None:
            sent.append((to, body))

    import app.services.auth_service as auth_service_module

    original_get_provider = auth_service_module.get_email_provider
    auth_service_module.get_email_provider = lambda: _CapturingEmailProvider()
    try:
        await auth_service.request_password_reset(db_session, email=user.email)
    finally:
        auth_service_module.get_email_provider = original_get_provider

    assert len(sent) == 1
    reset_link_body = sent[0][1]
    reset_token = reset_link_body.split("token=")[1]

    await auth_service.reset_password(db_session, token=reset_token, new_password="senha-nova-123")

    with pytest.raises(AuthenticationError):
        await auth_service.login(db_session, email=user.email, password="senha-antiga")
    await auth_service.login(db_session, email=user.email, password="senha-nova-123")

    # The pre-reset session must be dead now, not just the password.
    with pytest.raises(AuthenticationError):
        await auth_service.refresh(db_session, raw_refresh_token=pre_reset_tokens.refresh_token)


@pytest.mark.asyncio
async def test_password_reset_token_cannot_be_replayed(db_session: AsyncSession, make_tenant):
    tenant_id = await make_tenant()
    user = await _seed_admin(db_session, tenant_id, password="senha-antiga")

    from app.core.security import create_password_reset_token

    reset_token = create_password_reset_token(
        user_id=user.id, tenant_id=tenant_id, current_password_hash=user.password_hash
    )

    await auth_service.reset_password(db_session, token=reset_token, new_password="senha-nova-123")

    with pytest.raises(AuthenticationError):
        await auth_service.reset_password(db_session, token=reset_token, new_password="outra-senha-999")


def test_require_role_allows_matching_role():
    # require_role's inner function takes current_user via Depends() in real
    # requests (that's just a default value); calling it directly with a
    # positional arg exercises the same logic without needing FastAPI's DI.
    current_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=UserRole.ADMIN)
    checker = require_role(UserRole.ADMIN, UserRole.MANAGER)
    assert checker(current_user) is current_user


def test_require_role_denies_non_matching_role():
    checker = require_role(UserRole.ADMIN)
    current_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role=UserRole.EMPLOYEE)

    with pytest.raises(PermissionDeniedError):
        checker(current_user)
