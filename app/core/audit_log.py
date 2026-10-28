import hashlib
import logging
import uuid

from fastapi import Request
from slowapi.util import get_remote_address

from app.core.logging_config import AUDIT_LOGGER_NAME

logger = logging.getLogger(AUDIT_LOGGER_NAME)


def hash_email(email: str) -> str:
    """Identificador del email para correlacionar eventos sin guardar el email.

    SHA-256 del email normalizado, primeros 16 caracteres hexadecimales.
    """
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def log_login_succeeded(request: Request, user_id: uuid.UUID, email: str) -> None:
    logger.info(
        "Login exitoso",
        extra={
            "event": "login_succeeded",
            "client_ip": get_remote_address(request),
            "email_hash": hash_email(email),
            "user_id": str(user_id),
        },
    )


def log_login_failed(request: Request, email: str) -> None:
    logger.warning(
        "Login fallido",
        extra={
            "event": "login_failed",
            "client_ip": get_remote_address(request),
            "email_hash": hash_email(email),
        },
    )


def log_login_rate_limited(request: Request) -> None:
    logger.warning(
        "Login bloqueado por exceso de intentos",
        extra={
            "event": "login_rate_limited",
            "client_ip": get_remote_address(request),
            "path": request.url.path,
        },
    )