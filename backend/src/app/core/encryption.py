from cryptography.fernet import Fernet

from app.core.config import get_settings

settings = get_settings()


def encrypt_secret(plaintext: str) -> str:
    """Reversible symmetric encryption for secrets we must recover in plaintext
    later (e.g. a tenant's SMTP password, needed to authenticate with their
    mail server) -- unlike every other secret this app stores (refresh
    tokens, user passwords), which are hashed one-way in core/security.py
    because they only ever need to be verified, never read back.
    """
    return Fernet(settings.smtp_credentials_encryption_key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    return Fernet(settings.smtp_credentials_encryption_key).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
