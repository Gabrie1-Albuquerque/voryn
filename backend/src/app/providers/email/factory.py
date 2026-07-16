from functools import lru_cache

from app.core.config import get_settings
from app.providers.email.base import EmailProvider
from app.providers.email.console_provider import ConsoleEmailProvider


@lru_cache
def get_email_provider() -> EmailProvider:
    provider = get_settings().email_provider
    if provider == "console":
        return ConsoleEmailProvider()
    if provider == "smtp":
        from app.providers.email.smtp_provider import SmtpEmailProvider

        return SmtpEmailProvider()
    raise ValueError(f"unknown EMAIL_PROVIDER: {provider!r}")
