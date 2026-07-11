class AppError(Exception):
    """Base for domain errors that routers/main.py exception handlers translate
    to HTTP responses, so services never import FastAPI/HTTPException.
    """


class AuthenticationError(AppError):
    """Invalid credentials, invalid/expired/malformed token -> 401."""


class PermissionDeniedError(AppError):
    """Authenticated, but not allowed to perform this action -> 403."""


class NotFoundError(AppError):
    """-> 404."""


class ConflictError(AppError):
    """-> 409. e.g. scheduling conflicts, a unique constraint violation surfaced as a domain concept."""
