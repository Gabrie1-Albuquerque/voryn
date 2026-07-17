from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Plataforma Inteligente de Agendamentos"
    environment: str = "development"
    debug: bool = True

    # Restricted, non-superuser role -- this is what the running app and worker
    # use for every request. Row-Level Security only works as a real defense
    # (not just documentation) against a role that cannot bypass it, so this
    # must never point at the Postgres superuser role.
    database_url: str = "postgresql+asyncpg://app_runtime:app_runtime@postgres:5432/app"
    # Superuser/owner role, used ONLY by Alembic: creating types/tables/RLS
    # policies and the app_runtime role itself requires ownership privileges
    # that app_runtime deliberately does not have.
    migrations_database_url: str = "postgresql+asyncpg://app:app@postgres:5432/app"
    app_runtime_db_password: str = "app_runtime"

    redis_url: str = "redis://redis:6379/0"

    # Placeholder only, long enough to not trip PyJWT's minimum-key-length
    # warning -- .env.example instructs generating a real random secret
    # (`openssl rand -hex 32`) before any real deployment.
    jwt_secret_key: str = "change-me-in-.env-this-is-a-placeholder-not-a-real-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    # Base URL the frontend is served at, used to build links sent in emails
    # (password reset, etc.) -- not an API base, a browser-facing one.
    public_app_url: str = "http://localhost:8080"

    notification_provider: str = "console"  # console | whatsapp_cloud | zapi
    payment_provider: str = "mock"  # mock | mercadopago
    email_provider: str = "console"  # console | smtp

    # Encrypts each tenant's SMTP password at rest (Company.smtp_password_encrypted)
    # so it can be decrypted again to authenticate with their mail server --
    # a reversible cipher, not a hash, unlike every other secret this app
    # stores (refresh tokens, user passwords). Deliberately NOT a valid Fernet
    # key (unlike jwt_secret_key's placeholder, which works out of the box) --
    # a real, working default here would mean anyone reading this public repo
    # could decrypt any tenant's SMTP password if a deployer forgot to set
    # their own. Fernet() raises immediately on this value; .env.example
    # instructs generating a real one before any tenant connects an account.
    # Losing/rotating the real key without a re-encryption migration makes
    # every stored SMTP password permanently undecryptable -- accepted,
    # documented risk, not solved here.
    smtp_credentials_encryption_key: str = "change-me-in-.env-generate-a-real-fernet-key-not-this"

    # How often workers/scheduler.py's periodic tick runs. The reminder scan
    # window (workers/reminders.py) is sized to match this exactly, so every
    # appointment's 24h/2h-before instant gets caught in exactly one tick.
    reminder_scan_interval_minutes: int = 5

    mercadopago_access_token: str | None = None
    mercadopago_webhook_secret: str | None = None

    whatsapp_cloud_token: str | None = None
    whatsapp_cloud_phone_number_id: str | None = None
    # Meta's webhook registration handshake (GET with hub.verify_token) checks
    # against this. One value for the whole app rather than per-tenant: the
    # Company model has no per-tenant WhatsApp credential storage yet, and a
    # single Meta Business App covering every tenant is the simpler starting
    # shape for a bootstrapped SaaS.
    whatsapp_webhook_verify_token: str = "change-me-in-.env"
    zapi_instance_id: str | None = None
    zapi_token: str | None = None

    # Self-hosted Evolution API (WhatsApp bridge): one deployment, one
    # instance per tenant, named by company slug -- see
    # providers/notifications/evolution_provider.py. URL is the
    # compose-internal address; the service is never exposed publicly.
    evolution_api_url: str | None = "http://evolution:8080"
    evolution_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
