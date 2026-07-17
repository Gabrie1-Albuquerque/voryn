from functools import lru_cache

from app.core.config import get_settings
from app.providers.notifications.base import NotificationProvider
from app.providers.notifications.console_provider import ConsoleNotificationProvider


@lru_cache
def get_notification_provider() -> NotificationProvider:
    provider = get_settings().notification_provider
    if provider == "console":
        return ConsoleNotificationProvider()
    if provider == "whatsapp_cloud":
        from app.providers.notifications.whatsapp_cloud_provider import WhatsAppCloudProvider

        return WhatsAppCloudProvider()
    if provider == "zapi":
        from app.providers.notifications.zapi_provider import ZApiProvider

        return ZApiProvider()
    if provider == "evolution":
        from app.providers.notifications.evolution_provider import EvolutionApiProvider

        return EvolutionApiProvider()
    raise ValueError(f"unknown NOTIFICATION_PROVIDER: {provider!r}")
