import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import AppError, AuthenticationError, ConflictError, NotFoundError, PermissionDeniedError
from app.routers import auth

# Without this, app.* loggers (e.g. the console notification/email/payment
# providers) are silently swallowed: a logger with no handler configured
# anywhere in its ancestor chain only surfaces WARNING+ via Python's
# "handler of last resort", so provider.info(...) calls -- the entire
# point of the console providers in local dev -- would produce no visible
# output at all.
logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(title=settings.app_name)

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
}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    status_code = next((code for cls, code in _STATUS_BY_ERROR.items() if isinstance(exc, cls)), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
