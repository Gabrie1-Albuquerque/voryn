import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_secret, encrypt_secret
from app.providers.email.smtp_provider import _tls_kwargs
from app.schemas.company import CompanyResponse, CompanyUpdateRequest
from app.services import company_service


def test_encrypt_decrypt_round_trip():
    plaintext = "senha-de-app-super-secreta"
    ciphertext = encrypt_secret(plaintext)

    assert ciphertext != plaintext
    assert decrypt_secret(ciphertext) == plaintext


def test_tls_kwargs_uses_implicit_tls_only_for_port_465():
    assert _tls_kwargs(465) == {"use_tls": True}
    assert _tls_kwargs(587) == {"start_tls": True}
    assert _tls_kwargs(25) == {"start_tls": True}


@pytest.mark.asyncio
async def test_update_company_encrypts_smtp_password_and_never_returns_it(
    db_session: AsyncSession, make_tenant
):
    tenant_id: uuid.UUID = await make_tenant()

    company = await company_service.update_company(
        db_session,
        tenant_id,
        CompanyUpdateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="contato@salao.example.com",
            smtp_password="minha-senha-de-app",
            smtp_from_email="contato@salao.example.com",
        ),
    )

    # Stored value is a Fernet ciphertext, not the plaintext password, and
    # round-trips back to it.
    assert company.smtp_password_encrypted is not None
    assert company.smtp_password_encrypted != "minha-senha-de-app"
    assert decrypt_secret(company.smtp_password_encrypted) == "minha-senha-de-app"

    # CompanyResponse never exposes the password or its ciphertext, only the
    # derived "is something configured" boolean.
    response = CompanyResponse.model_validate(company, from_attributes=True)
    assert not hasattr(response, "smtp_password")
    assert not hasattr(response, "smtp_password_encrypted")
    assert response.smtp_configured is True


@pytest.mark.asyncio
async def test_update_company_omitting_smtp_password_keeps_existing_one(
    db_session: AsyncSession, make_tenant
):
    tenant_id: uuid.UUID = await make_tenant()
    await company_service.update_company(
        db_session,
        tenant_id,
        CompanyUpdateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="contato@salao.example.com",
            smtp_password="senha-original",
            smtp_from_email="contato@salao.example.com",
        ),
    )

    # A later patch that only changes the host must not wipe/alter the
    # already-saved password (exclude_unset=True semantics).
    company = await company_service.update_company(
        db_session, tenant_id, CompanyUpdateRequest(smtp_host="smtp2.example.com")
    )

    assert company.smtp_host == "smtp2.example.com"
    assert decrypt_secret(company.smtp_password_encrypted) == "senha-original"
