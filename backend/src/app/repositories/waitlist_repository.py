import uuid
from datetime import datetime

from sqlalchemy import or_, select

from app.models.appointment import WaitlistEntry
from app.models.enums import WaitlistStatus
from app.repositories.base import TenantScopedRepository


class WaitlistRepository(TenantScopedRepository[WaitlistEntry]):
    model = WaitlistEntry

    async def find_oldest_match(
        self, *, service_id: uuid.UUID, employee_id: uuid.UUID, slot_start: datetime
    ) -> WaitlistEntry | None:
        """Oldest-first match for a slot that just freed up (see
        appointment_service.cancel_appointment, which calls this
        synchronously rather than waiting for a periodic scan -- lower
        latency, and simpler than coordinating with the reminder scan's
        schedule). preferred_employee_id NULL means "any employee is fine".
        """
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.tenant_id == self.tenant_id,
                WaitlistEntry.status == WaitlistStatus.WAITING,
                WaitlistEntry.service_id == service_id,
                or_(WaitlistEntry.preferred_employee_id.is_(None), WaitlistEntry.preferred_employee_id == employee_id),
                WaitlistEntry.preferred_window_start <= slot_start,
                WaitlistEntry.preferred_window_end >= slot_start,
            )
            .order_by(WaitlistEntry.created_at)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
