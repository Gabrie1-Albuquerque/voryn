import uuid

from sqlalchemy import select

from app.models.enums import NotificationType
from app.models.notification import NotificationLog
from app.repositories.base import TenantScopedRepository


class NotificationRepository(TenantScopedRepository[NotificationLog]):
    model = NotificationLog

    async def already_sent(self, appointment_id: uuid.UUID, notification_type: NotificationType) -> bool:
        """The idempotency check the periodic reminder scan relies on so it
        can run at any frequency without double-sending: a (appointment_id,
        notification_type) pair already logged means skip.
        """
        stmt = select(NotificationLog.id).where(
            NotificationLog.tenant_id == self.tenant_id,
            NotificationLog.appointment_id == appointment_id,
            NotificationLog.notification_type == notification_type,
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.first() is not None
