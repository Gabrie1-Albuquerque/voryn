from sqlalchemy import select

from app.models.client import Client, ClientNote
from app.repositories.base import TenantScopedRepository


class ClientRepository(TenantScopedRepository[Client]):
    model = Client


class ClientNoteRepository(TenantScopedRepository[ClientNote]):
    model = ClientNote

    async def list_for_client(self, client_id) -> list[ClientNote]:
        stmt = (
            select(ClientNote)
            .where(ClientNote.tenant_id == self.tenant_id, ClientNote.client_id == client_id)
            .order_by(ClientNote.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
