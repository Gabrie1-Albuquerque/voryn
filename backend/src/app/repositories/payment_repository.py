from sqlalchemy import select

from app.models.payment import PaymentRecord
from app.repositories.base import TenantScopedRepository


class PaymentRecordRepository(TenantScopedRepository[PaymentRecord]):
    model = PaymentRecord

    async def get_by_provider_reference(self, provider_reference_id: str) -> PaymentRecord | None:
        stmt = select(PaymentRecord).where(
            PaymentRecord.tenant_id == self.tenant_id,
            PaymentRecord.provider_reference_id == provider_reference_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
