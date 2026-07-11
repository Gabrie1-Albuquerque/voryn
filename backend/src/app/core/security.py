import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models.enums import UserRole

settings = get_settings()

# Lives here (not core/deps.py or core/database.py) because both of those
# need it and importing it from either of them into the other would be
# circular; security.py is a leaf module neither depends on.
# tokenUrl only populates OpenAPI's "Authorize" button (path as FastAPI
# itself sees it, without the /api prefix nginx strips before proxying
# here); the actual login endpoint is JSON, not form-encoded, unlike the
# OAuth2 password flow this class is nominally modeling.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
# Argon2 (pwdlib's recommended default): passlib -- the older, more common
# choice -- has an unresolved compatibility break with current bcrypt
# releases (its version-sniffing expects an attribute recent bcrypt versions
# removed), so this uses pwdlib, the actively-maintained replacement, instead.
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def _encode(claims: dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**claims, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID, role: UserRole) -> str:
    return _encode(
        {"sub": str(user_id), "tenant_id": str(tenant_id), "role": role.value, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError (expired, bad signature, malformed) on any failure -- callers translate to 401."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token(tenant_id: uuid.UUID) -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Only the hash is stored server-side
    (in the refresh_tokens table) so a DB leak alone doesn't hand out valid
    sessions -- the same reasoning as storing password hashes, not passwords.

    The raw token is prefixed with the plain tenant_id (e.g.
    "3fae.../<random>"). Refresh requests hit the API with no JWT to read a
    tenant claim from, so something has to tell us which tenant's RLS
    context to set before we can even look the token up -- same
    chicken-and-egg as login, solved here by routing on a non-secret prefix
    instead of a second SECURITY DEFINER function. Tenant id isn't sensitive
    (it's already visible in every access token's claims); the actual secret
    is the random suffix.
    """
    raw = f"{tenant_id}.{secrets.token_urlsafe(48)}"
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def parse_refresh_token_tenant(raw_token: str) -> uuid.UUID:
    """Raises ValueError on a malformed token -- callers translate to 401."""
    prefix, _, _ = raw_token.partition(".")
    return uuid.UUID(prefix)


def _password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class PasswordResetClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID


def create_password_reset_token(
    *, user_id: uuid.UUID, tenant_id: uuid.UUID, current_password_hash: str
) -> str:
    """Stateless (no DB row): self-invalidating by embedding a fingerprint of
    the CURRENT password hash. Once the password actually changes, replaying
    this same token fails the fingerprint check below even though the JWT
    signature/expiry are still otherwise valid -- a single DB table's worth
    of "was this used" bookkeeping without an actual table. tenant_id rides
    along in the claims (like the access token) so reset_password can
    set_tenant_context and look the user up through the normal RLS-protected
    path instead of needing another pre-tenant-context lookup function.
    """
    return _encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "purpose": "password_reset",
            "pwd_fp": _password_fingerprint(current_password_hash),
        },
        timedelta(minutes=30),
    )


def decode_password_reset_token(token: str) -> PasswordResetClaims:
    """Decodes and checks purpose/expiry/signature only -- NOT the password
    fingerprint, since that requires a DB lookup the caller does afterwards
    (once it has tenant_id from here to set RLS context). Raises
    jwt.PyJWTError or ValueError; callers translate both to a single generic
    "invalid or expired link".
    """
    claims = decode_token(token)
    if claims.get("purpose") != "password_reset":
        raise ValueError("token is not a password reset token")
    return PasswordResetClaims(user_id=uuid.UUID(claims["sub"]), tenant_id=uuid.UUID(claims["tenant_id"]))


def verify_password_reset_fingerprint(token: str, *, current_password_hash: str) -> None:
    """Raises ValueError if the token was already used / the password has
    changed since issuance. Call after decode_password_reset_token, once the
    caller has fetched the user's current password_hash.
    """
    claims = decode_token(token)
    if claims.get("pwd_fp") != _password_fingerprint(current_password_hash):
        raise ValueError("token already used or password changed since issuance")
