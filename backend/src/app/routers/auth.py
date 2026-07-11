from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, get_tenant_db
from app.core.exceptions import NotFoundError
from app.repositories.user_repository import UserRepository
from app.services import auth_service
from app.schemas.auth import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPairResponse,
)

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> CurrentUserResponse:
    user = await UserRepository(db, current_user.tenant_id).get(current_user.user_id)
    if user is None:
        raise NotFoundError("user not found")
    return CurrentUserResponse(id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role.value)


@router.post("/login", response_model=TokenPairResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
    tokens = await auth_service.login(db, email=body.email, password=body.password)
    return TokenPairResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPairResponse:
    tokens = await auth_service.refresh(db, raw_refresh_token=body.refresh_token)
    return TokenPairResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await auth_service.logout(db, raw_refresh_token=body.refresh_token)
    return MessageResponse(message="logged out")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await auth_service.request_password_reset(db, email=body.email)
    # Always the same response, whether or not the email exists -- see
    # auth_service.request_password_reset's docstring.
    return MessageResponse(message="se o email existir, enviamos um link de redefinição de senha")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await auth_service.reset_password(db, token=body.token, new_password=body.new_password)
    return MessageResponse(message="senha redefinida com sucesso")
