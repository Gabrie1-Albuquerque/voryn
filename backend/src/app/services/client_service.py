import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.client import Client, ClientNote
from app.repositories.client_repository import ClientNoteRepository, ClientRepository
from app.schemas.client import ClientCreateRequest, ClientNoteCreateRequest, ClientUpdateRequest


async def list_clients(session: AsyncSession, tenant_id: uuid.UUID) -> list[Client]:
    return await ClientRepository(session, tenant_id).list()


async def get_client(session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    client = await ClientRepository(session, tenant_id).get(client_id)
    if client is None:
        raise NotFoundError("client not found")
    return client


async def create_client(session: AsyncSession, tenant_id: uuid.UUID, data: ClientCreateRequest) -> Client:
    client = ClientRepository(session, tenant_id).add(Client(**data.model_dump()))
    await session.flush()
    return client


async def update_client(
    session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID, data: ClientUpdateRequest
) -> Client:
    client = await get_client(session, tenant_id, client_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await session.flush()
    return client


async def deactivate_client(session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID) -> None:
    client = await get_client(session, tenant_id, client_id)
    client.is_active = False
    await session.flush()


async def list_notes(session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID) -> list[ClientNote]:
    await get_client(session, tenant_id, client_id)  # 404s if missing/other tenant
    return await ClientNoteRepository(session, tenant_id).list_for_client(client_id)


async def add_note(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    author_user_id: uuid.UUID,
    data: ClientNoteCreateRequest,
) -> ClientNote:
    await get_client(session, tenant_id, client_id)  # 404s if missing/other tenant
    note = ClientNoteRepository(session, tenant_id).add(
        ClientNote(
            client_id=client_id,
            author_user_id=author_user_id,
            note_type=data.note_type,
            body=data.body,
            appointment_id=data.appointment_id,
        )
    )
    await session.flush()
    return note
