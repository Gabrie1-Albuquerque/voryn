import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.core.database import SlugTenantContext, get_tenant_db_by_slug
from app.core.exceptions import AuthenticationError
from app.repositories.client_repository import ClientRepository
from app.services import appointment_service, payment_service
from app.providers.notifications.factory import get_notification_provider

router = APIRouter()
logger = logging.getLogger("app.webhooks")
settings = get_settings()


@router.get("/whatsapp/{company_slug}", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    company_slug: str,
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> str:
    """Meta's one-time webhook registration handshake: register this exact
    URL (per tenant, via company_slug) in the Meta Business App's webhook
    config, and Meta calls this to confirm ownership before it'll ever send
    a real inbound message. company_slug isn't used for anything here beyond
    matching the route shape real inbound webhooks will hit -- the check
    itself is purely the verify token.
    """
    if hub_mode != "subscribe" or hub_verify_token != settings.whatsapp_webhook_verify_token:
        raise AuthenticationError("invalid webhook verification request")
    return hub_challenge


@router.post("/whatsapp/{company_slug}")
async def receive_whatsapp_webhook(
    request: Request,
    ctx: SlugTenantContext = Depends(get_tenant_db_by_slug),
) -> dict[str, str]:
    payload = await request.json()
    provider = get_notification_provider()
    message = await provider.parse_inbound_webhook(payload)
    if message is None:
        return {"status": "ignored"}

    client_repo = ClientRepository(ctx.session, ctx.tenant_id)
    clients = await client_repo.list(phone=message.from_phone)
    if not clients:
        logger.info("inbound WhatsApp from unknown phone=%s tenant=%s", message.from_phone, ctx.tenant_id)
        return {"status": "ignored"}

    appointment = await appointment_service.find_next_actionable_appointment_for_client(
        ctx.session, ctx.tenant_id, clients[0].id
    )
    if appointment is None:
        return {"status": "ignored"}

    reply = message.body.strip()
    # Same transition entrypoints the staff dashboard buttons call -- no
    # parallel "confirm via WhatsApp" logic, so both paths stay consistent.
    if reply == "1":
        await appointment_service.confirm_appointment(
            ctx.session, ctx.tenant_id, appointment.id, changed_by="client_whatsapp"
        )
        return {"status": "confirmed"}
    if reply == "2":
        await appointment_service.cancel_appointment(
            ctx.session, ctx.tenant_id, appointment.id, changed_by="client_whatsapp"
        )
        return {"status": "cancelled"}

    return {"status": "unrecognized"}


@router.post("/mercadopago")
async def receive_mercadopago_webhook(request: Request) -> dict[str, str]:
    """One global endpoint (no per-tenant slug, unlike the WhatsApp webhook
    above): Mercado Pago notifications don't carry any tenant info we don't
    put there ourselves, so tenant is resolved from the external_reference
    embedded when the charge was created (see payment_service.py), not from
    the URL -- handle_mercadopago_webhook manages its own DB session once
    that's parsed out, since none exists yet at this point.
    """
    payload = await request.json()
    await payment_service.handle_mercadopago_webhook(payload, dict(request.headers))
    return {"status": "ok"}
