import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_tenant_db
from app.core.deps import CurrentUser, require_role
from app.models.enums import UserRole
from app.schemas.client import (
    ClientCreateRequest,
    ClientNoteCreateRequest,
    ClientNoteResponse,
    ClientResponse,
    ClientUpdateRequest,
)
from app.services import client_service

router = APIRouter()

# Funcionário needs client info to perform their service (see plan's RBAC
# shape), so client CRUD is open to all three roles, unlike catalog/staff
# management which is ADMIN/MANAGER only.
_ANY_ROLE = require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EMPLOYEE)


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    current_user: CurrentUser = Depends(_ANY_ROLE), db: AsyncSession = Depends(get_tenant_db)
) -> list[ClientResponse]:
    clients = await client_service.list_clients(db, current_user.tenant_id)
    return [ClientResponse.model_validate(c, from_attributes=True) for c in clients]


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    body: ClientCreateRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClientResponse:
    client = await client_service.create_client(db, current_user.tenant_id, body)
    return ClientResponse.model_validate(client, from_attributes=True)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClientResponse:
    client = await client_service.get_client(db, current_user.tenant_id, client_id)
    return ClientResponse.model_validate(client, from_attributes=True)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdateRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClientResponse:
    client = await client_service.update_client(db, current_user.tenant_id, client_id, body)
    return ClientResponse.model_validate(client, from_attributes=True)


@router.delete("/{client_id}", status_code=204)
async def deactivate_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    await client_service.deactivate_client(db, current_user.tenant_id, client_id)


@router.get("/{client_id}/notes", response_model=list[ClientNoteResponse])
async def list_client_notes(
    client_id: uuid.UUID,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[ClientNoteResponse]:
    notes = await client_service.list_notes(db, current_user.tenant_id, client_id)
    return [ClientNoteResponse.model_validate(n, from_attributes=True) for n in notes]


@router.post("/{client_id}/notes", response_model=ClientNoteResponse, status_code=201)
async def add_client_note(
    client_id: uuid.UUID,
    body: ClientNoteCreateRequest,
    current_user: CurrentUser = Depends(_ANY_ROLE),
    db: AsyncSession = Depends(get_tenant_db),
) -> ClientNoteResponse:
    note = await client_service.add_note(db, current_user.tenant_id, client_id, current_user.user_id, body)
    return ClientNoteResponse.model_validate(note, from_attributes=True)
