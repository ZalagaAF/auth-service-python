from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.core.audit_log import log_login_rate_limited

LOGIN_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT = f"{LOGIN_MAX_ATTEMPTS}/minute"
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60

# La clave es la IP de la conexión (no X-Forwarded-For, que el cliente puede falsificar).
# Los contadores viven en la memoria del proceso.
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    log_login_rate_limited(request)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Demasiados intentos. Intente de nuevo más tarde."},
        # Cota superior honesta: la duración de la ventana del límite.
        headers={"Retry-After": str(LOGIN_RATE_LIMIT_WINDOW_SECONDS)},
    )