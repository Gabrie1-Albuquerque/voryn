from functools import lru_cache

from app.core.config import get_settings
from app.providers.payments.base import PaymentProvider
from app.providers.payments.mock_provider import MockPaymentProvider


@lru_cache
def get_payment_provider() -> PaymentProvider:
    provider = get_settings().payment_provider
    if provider == "mock":
        return MockPaymentProvider()
    if provider == "mercadopago":
        from app.providers.payments.mercadopago_provider import MercadoPagoProvider

        return MercadoPagoProvider()
    raise ValueError(f"unknown PAYMENT_PROVIDER: {provider!r}")
