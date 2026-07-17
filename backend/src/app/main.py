import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.routers import (
    appointments,
    auth,
    clients,
    companies,
    dashboard,
    employees,
    payments,
    public_booking,
    rooms,
    services,
    waitlist,
    webhooks,
)

# Without this, app.* loggers (e.g. the console notification/email/payment
# providers) are silently swallowed: a logger with no handler configured
# anywhere in its ancestor chain only surfaces WARNING+ via Python's
# "handler of last resort", so provider.info(...) calls -- the entire
# point of the console providers in local dev -- would produce no visible
# output at all.
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")

settings = get_settings()

# Interactive API docs (/docs, /redoc, /openapi.json) expose the full API
# surface -- fine in dev, needless disclosure in production. Disabled there.
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if settings.environment == "production"
    else {}
)
app = FastAPI(title=settings.app_name, **_docs_kwargs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATUS_BY_ERROR = {
    AuthenticationError: 401,
    PermissionDeniedError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    ValidationError: 400,
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_code = next((code for cls, code in _STATUS_BY_ERROR.items() if isinstance(exc, cls)), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(employees.router, prefix="/employees", tags=["employees"])
app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(services.router, prefix="/services", tags=["services"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
# No prefix: payments.router's own paths are already "/appointments/{id}/deposit"
# (an action on the appointment resource, not a separate top-level "payments" one).
app.include_router(payments.router, tags=["payments"])
app.include_router(waitlist.router, prefix="/waitlist", tags=["waitlist"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(public_booking.router, prefix="/public", tags=["public-booking"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
