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


class ValidationError(AppError):
    """-> 400. Business-rule validation that can't be expressed as a Pydantic
    schema constraint alone -- typically because it only applies after
    merging a partial update (PATCH) with existing state, unlike a create
    request's shape, which Pydantic validators already cover.
    """
