import logging

from app.providers.email.base import EmailProvider

logger = logging.getLogger("app.email")


class ConsoleEmailProvider(EmailProvider):
    """Local-dev default: logs instead of sending, so the whole password-recovery
    flow is exercisable end-to-end with zero external credentials.
    """

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL to=%s subject=%r\n%s", to, subject, body)
