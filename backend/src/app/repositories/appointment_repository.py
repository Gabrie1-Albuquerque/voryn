import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.repositories.base import TenantScopedRepository


class AppointmentRepository(TenantScopedRepository[Appointment]):
    model = Appointment

    def _with_relations(self):
        # See employee_repository.py's identical comment: populate_existing
        # matters here too, since reschedule/confirm/cancel all re-fetch an
        # object that's already in the session's identity map.
        return (
            select(Appointment)
            .options(
                selectinload(Appointment.client),
                selectinload(Appointment.employee),
                selectinload(Appointment.service),
                selectinload(Appointment.room),
            )
            .execution_options(populate_existing=True)
        )

    async def get_with_relations(self, id: uuid.UUID) -> Appointment | None:
        stmt = self._with_relations().where(Appointment.id == id, Appointment.tenant_id == self.tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_in_range(
        self, start: datetime, end: datetime, *, employee_id: uuid.UUID | None = None
    ) -> list[Appointment]:
        stmt = self._with_relations().where(
            Appointment.tenant_id == self.tenant_id,
            Appointment.starts_at < end,
            Appointment.ends_at > start,
        )
        if employee_id is not None:
            stmt = stmt.where(Appointment.employee_id == employee_id)
        stmt = stmt.order_by(Appointment.starts_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
