import logging
from email.message import EmailMessage

import aiosmtplib

from app.providers.email.base import EmailProvider, SmtpConfig

logger = logging.getLogger("app.email")

# Port 465 is implicit TLS (connect already encrypted); everything else
# (587, the modern default; legacy 25) is STARTTLS (plain connect, then
# upgrade) -- covers the overwhelming majority of real mail providers
# without needing a separate "encryption mode" field in the UI.
_IMPLICIT_TLS_PORT = 465


def _tls_kwargs(port: int) -> dict:
    if port == _IMPLICIT_TLS_PORT:
        return {"use_tls": True}
    return {"start_tls": True}


class SmtpEmailProvider(EmailProvider):
    """Sends through a tenant's own mail account (Company.smtp_*) rather than
    a shared platform credential -- see SmtpConfig's docstring. Requires
    smtp_config on every call; there's no app-wide fallback credential like
    Mercado Pago/WhatsApp Cloud have, because the whole point is that each
    business sends as itself.
    """

    async def send(
        self, *, to: str, subject: str, body: str, smtp_config: SmtpConfig | None = None
    ) -> None:
        if smtp_config is None:
            raise ValueError("SmtpEmailProvider.send() requires smtp_config")

        message = EmailMessage()
        message["From"] = smtp_config.from_email
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=smtp_config.host,
            port=smtp_config.port,
            username=smtp_config.username,
            password=smtp_config.password,
            timeout=15.0,
            **_tls_kwargs(smtp_config.port),
        )


async def test_connection(smtp_config: SmtpConfig) -> tuple[bool, str]:
    """Connects and authenticates only -- no message sent -- so the settings
    screen can validate credentials before they're ever persisted. Never
    includes smtp_config.password (or any other exception detail that might
    echo it back) in the returned message.
    """
    try:
        async with aiosmtplib.SMTP(
            hostname=smtp_config.host,
            port=smtp_config.port,
            username=smtp_config.username,
            password=smtp_config.password,
            timeout=15.0,
            **_tls_kwargs(smtp_config.port),
        ):
            pass
    except aiosmtplib.SMTPAuthenticationError:
        return False, "Não foi possível autenticar -- confira usuário e senha."
    except Exception:
        logger.exception("smtp test_connection failed for host=%s port=%s", smtp_config.host, smtp_config.port)
        return False, "Não foi possível conectar ao servidor -- confira host e porta."
    return True, "Conexão bem-sucedida."
