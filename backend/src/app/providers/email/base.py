from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SmtpConfig:
    """A tenant's own mail account (Company.smtp_*, see models/tenant.py).
    Passed per-call rather than read from global settings -- unlike every
    other provider in this codebase (Mercado Pago, WhatsApp Cloud), which
    reads one shared, app-wide credential.
    """

    host: str
    port: int
    username: str
    password: str
    from_email: str


class EmailProvider(ABC):
    @abstractmethod
    async def send(
        self, *, to: str, subject: str, body: str, smtp_config: SmtpConfig | None = None
    ) -> None:
        """smtp_config is None for platform-level email (e.g. auth_service.py's
        password reset, which is Voryn's own login system, not a tenant's
        client-facing message) and required for tenant-notification email
        (see notification_service.py) -- ConsoleEmailProvider ignores it
        either way; SmtpEmailProvider requires it.
        """
        ...
