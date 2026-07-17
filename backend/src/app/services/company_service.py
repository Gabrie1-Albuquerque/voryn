import logging
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.encryption import encrypt_secret
from app.core.exceptions import NotFoundError, ValidationError
from app.models.tenant import Company
from app.providers.email.base import SmtpConfig
from app.providers.email.smtp_provider import test_connection as _test_smtp_connection
from app.schemas.company import CompanyUpdateRequest, MercadoPagoTestRequest, SmtpTestRequest

logger = logging.getLogger("app.company")
settings = get_settings()


async def get_company(session: AsyncSession, tenant_id: uuid.UUID) -> Company:
    # Company IS the tenant (no tenant_id column of its own), so this is a
    # plain get-by-id, not a TenantScopedRepository -- there's no broader
    # "list all companies" operation for a tenant-scoped caller to abuse.
    company = await session.get(Company, tenant_id)
    if company is None:
        raise NotFoundError("company not found")
    return company


async def update_company(session: AsyncSession, tenant_id: uuid.UUID, data: CompanyUpdateRequest) -> Company:
    company = await get_company(session, tenant_id)
    payload = data.model_dump(exclude_unset=True)
    # Write-only secrets (schemas/company.py) with no matching plaintext
    # column -- the generic setattr loop below would fail on them, so encrypt
    # each into its *_encrypted column and pop it out first.
    if "smtp_password" in payload:
        company.smtp_password_encrypted = encrypt_secret(payload.pop("smtp_password"))
    if "mercadopago_access_token" in payload:
        company.mp_access_token_encrypted = encrypt_secret(payload.pop("mercadopago_access_token"))
    if "mercadopago_webhook_secret" in payload:
        company.mp_webhook_secret_encrypted = encrypt_secret(payload.pop("mercadopago_webhook_secret"))
    for field, value in payload.items():
        setattr(company, field, value)
    await session.commit()
    return company


async def test_smtp_connection(data: SmtpTestRequest) -> tuple[bool, str]:
    """Tests candidate SMTP credentials without persisting them -- see
    routers/companies.py's POST /me/test-smtp.
    """
    return await _test_smtp_connection(
        SmtpConfig(
            host=data.smtp_host,
            port=data.smtp_port,
            username=data.smtp_username,
            password=data.smtp_password,
            from_email=data.smtp_from_email,
        )
    )


async def test_mercadopago_token(data: MercadoPagoTestRequest) -> tuple[bool, str]:
    """Validates a candidate Mercado Pago access token with a cheap
    authenticated call, without persisting it. Also warns about TEST-
    tokens: receiving real money requires a production APP_USR- token
    (the inverse of the usual sandbox confusion).
    """
    if data.access_token.startswith("TEST-"):
        return False, (
            "Este é um token de TESTE (sandbox). Para receber pagamentos de verdade, "
            "use a credencial de produção (começa com APP_USR-)."
        )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.mercadopago.com/users/me",
                headers={"Authorization": f"Bearer {data.access_token}"},
            )
    except Exception:
        logger.exception("mercadopago token test request failed")
        return False, "Não foi possível falar com o Mercado Pago -- tente novamente."
    if response.status_code != 200:
        return False, "Token inválido -- confira se copiou a credencial de produção completa."
    nickname = response.json().get("nickname") or response.json().get("email") or "conta verificada"
    return True, f"Conectado à conta Mercado Pago: {nickname}"


def _evolution_headers() -> tuple[str, dict[str, str]]:
    if not settings.evolution_api_url or not settings.evolution_api_key:
        raise ValidationError("integração de WhatsApp não está configurada neste servidor")
    return settings.evolution_api_url.rstrip("/"), {"apikey": settings.evolution_api_key}


async def connect_whatsapp(session: AsyncSession, tenant_id: uuid.UUID) -> tuple[str, str | None]:
    """Creates (idempotently) the tenant's Evolution instance -- named by the
    company slug -- points its inbound webhook at this tenant's slugged
    WhatsApp webhook route, and returns (state, qr_base64) for the Settings
    screen to render. All request/response shapes verified empirically
    against Evolution v2.3.7 (see providers/notifications/evolution_provider.py).
    """
    company = await get_company(session, tenant_id)
    base, headers = _evolution_headers()
    instance = company.slug

    async with httpx.AsyncClient(timeout=30.0) as client:
        state_resp = await client.get(f"{base}/instance/connectionState/{instance}", headers=headers)
        if state_resp.status_code == 404:
            create_resp = await client.post(
                f"{base}/instance/create",
                headers=headers,
                json={"instanceName": instance, "integration": "WHATSAPP-BAILEYS", "qrcode": True},
            )
            create_resp.raise_for_status()
            qr = (create_resp.json().get("qrcode") or {}).get("base64")
            state = "connecting"
        else:
            state = (state_resp.json().get("instance") or {}).get("state", "close")
            if state == "open":
                # Still re-assert the webhook (below) even when connected, so
                # an instance created under the old public URL gets migrated
                # to the internal one on the next connect.
                await _set_whatsapp_webhook(client, base, headers, instance)
                return "open", None
            connect_resp = await client.get(f"{base}/instance/connect/{instance}", headers=headers)
            connect_resp.raise_for_status()
            qr = connect_resp.json().get("base64")

        # Idempotent: always (re)point the instance webhook at the INTERNAL
        # backend URL -- runs on create, reconnect, and already-open, so a
        # webhook set to the old public URL is corrected here.
        await _set_whatsapp_webhook(client, base, headers, instance)
        return state, qr


async def _set_whatsapp_webhook(client: "httpx.AsyncClient", base: str, headers: dict, instance: str) -> None:
    await client.post(
        f"{base}/webhook/set/{instance}",
        headers=headers,
        json={
            "webhook": {
                "enabled": True,
                # Internal address, not public: the inbound webhook acts on
                # the payload directly, so it must not be reachable from the
                # internet (nginx blocks /webhooks/whatsapp/ externally).
                "url": f"{settings.internal_webhook_base_url}/webhooks/whatsapp/{instance}",
                "events": ["MESSAGES_UPSERT"],
            }
        },
    )


async def whatsapp_status(session: AsyncSession, tenant_id: uuid.UUID) -> str:
    company = await get_company(session, tenant_id)
    base, headers = _evolution_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{base}/instance/connectionState/{company.slug}", headers=headers)
    if resp.status_code == 404:
        return "not_created"
    return (resp.json().get("instance") or {}).get("state", "close")
