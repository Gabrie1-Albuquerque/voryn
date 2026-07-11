from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Plataforma Inteligente de Agendamentos"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/app"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    notification_provider: str = "console"  # console | whatsapp_cloud | zapi
    payment_provider: str = "mock"  # mock | mercadopago
    email_provider: str = "console"

    mercadopago_access_token: str | None = None
    mercadopago_webhook_secret: str | None = None

    whatsapp_cloud_token: str | None = None
    whatsapp_cloud_phone_number_id: str | None = None
    zapi_instance_id: str | None = None
    zapi_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
