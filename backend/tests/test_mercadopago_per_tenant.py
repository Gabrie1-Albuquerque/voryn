import hashlib
import hmac
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_secret
from app.models.enums import PaymentProviderName
from app.providers.payments.mercadopago_provider import MercadoPagoConfig, MercadoPagoProvider
from app.providers.payments.mock_provider import MockPaymentProvider
from app.schemas.company import CompanyResponse, CompanyUpdateRequest
from app.services import company_service, payment_service


@pytest.mark.asyncio
async def test_update_company_encrypts_mp_credentials_and_never_returns_them(
    db_session: AsyncSession, make_tenant
):
    tenant_id: uuid.UUID = await make_tenant()

    company = await company_service.update_company(
        db_session,
        tenant_id,
        CompanyUpdateRequest(
            mercadopago_access_token="APP_USR-fake-token-123", mercadopago_webhook_secret="segredo-webhook"
        ),
    )

    assert company.mp_access_token_encrypted is not None
    assert "APP_USR-fake-token-123" not in company.mp_access_token_encrypted
    assert decrypt_secret(company.mp_access_token_encrypted) == "APP_USR-fake-token-123"
    assert decrypt_secret(company.mp_webhook_secret_encrypted) == "segredo-webhook"

    response = CompanyResponse.model_validate(company, from_attributes=True)
    assert response.mercadopago_configured is True
    assert not hasattr(response, "mercadopago_access_token")
    assert not hasattr(response, "mp_access_token_encrypted")


@pytest.mark.asyncio
async def test_provider_for_tenant_selects_mp_when_configured(db_session: AsyncSession, make_tenant):
    tenant_id: uuid.UUID = await make_tenant()

    provider, name = await payment_service._provider_for_tenant(db_session, tenant_id)
    assert isinstance(provider, MockPaymentProvider)
    assert name == PaymentProviderName.MOCK

    await company_service.update_company(
        db_session, tenant_id, CompanyUpdateRequest(mercadopago_access_token="APP_USR-abc")
    )
    provider, name = await payment_service._provider_for_tenant(db_session, tenant_id)
    assert isinstance(provider, MercadoPagoProvider)
    assert name == PaymentProviderName.MERCADOPAGO


def test_webhook_signature_verifies_with_tenant_secret():
    config = MercadoPagoConfig(access_token="APP_USR-x", webhook_secret="tenant-secret")
    provider = MercadoPagoProvider(config)

    payment_id = "12345"
    request_id = "req-abc"
    ts = "1721227200"
    manifest = f"id:{payment_id};request-id:{request_id};ts:{ts};"
    good_sig = hmac.new(b"tenant-secret", manifest.encode(), hashlib.sha256).hexdigest()

    headers_ok = {"x-signature": f"ts={ts},v1={good_sig}", "x-request-id": request_id}
    assert provider._verify_signature(payment_id=payment_id, headers=headers_ok) is True

    bad_sig = hmac.new(b"outro-secret", manifest.encode(), hashlib.sha256).hexdigest()
    headers_bad = {"x-signature": f"ts={ts},v1={bad_sig}", "x-request-id": request_id}
    assert provider._verify_signature(payment_id=payment_id, headers=headers_bad) is False


@pytest.mark.asyncio
async def test_tenant_webhook_rejects_mismatched_tenant_in_external_reference(
    db_session: AsyncSession, make_tenant, monkeypatch
):
    """A charge created under tenant A must never be mutable through tenant
    B's slugged webhook endpoint, even if a (fake) event passes parsing.
    """
    from app.providers.payments.base import WebhookEvent

    tenant_id: uuid.UUID = await make_tenant()
    other_tenant = uuid.uuid4()
    fake_record_id = uuid.uuid4()

    class _FakeProvider:
        async def parse_webhook(self, payload, headers):
            return WebhookEvent(
                provider_reference_id="999",
                status="approved",
                external_reference=f"{other_tenant}.{fake_record_id}",
            )

    async def _fake_provider_for_tenant(session, tid):
        return _FakeProvider(), PaymentProviderName.MERCADOPAGO

    monkeypatch.setattr(payment_service, "_provider_for_tenant", _fake_provider_for_tenant)

    # Must be a clean no-op: no exception, nothing mutated (the record id
    # doesn't even exist under this tenant).
    await payment_service.handle_tenant_mercadopago_webhook(db_session, tenant_id, {}, {})


@pytest.mark.asyncio
async def test_mock_provider_never_trusts_inbound_webhook():
    """Security: the global /webhooks/mercadopago runs the mock provider in
    production. If mock parsed the body, anyone could POST a forged
    "approved" event. It must always return None.
    """
    mock = MockPaymentProvider()
    forged = {"provider_reference_id": "x", "status": "approved", "external_reference": "a.b"}
    assert await mock.parse_webhook(forged, {}) is None
