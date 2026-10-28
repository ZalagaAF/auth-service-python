import json
import logging
import sys
from datetime import datetime, timezone

AUDIT_LOGGER_NAME = "auth.audit"

# Atributos que todo LogRecord trae por defecto. Lo que no esté acá es un campo "extra".
_STANDARD_ATTRIBUTES = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Escribe cada registro como una única línea de JSON."""

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRIBUTES:
                data[key] = value
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        # default=str convierte lo que JSON no sabe serializar (por ejemplo un UUID).
        # json.dumps escapa los saltos de línea: un valor no puede inyectar líneas falsas.
        return json.dumps(data, default=str, ensure_ascii=False)


class _StdoutHandler(logging.StreamHandler):
    """Como StreamHandler, pero resuelve sys.stdout en cada emisión.

    Así no queda atado a un flujo viejo si algo reemplaza sys.stdout
    (por ejemplo el captor de pytest). Es el mismo truco que usa la librería
    estándar con stderr.
    """

    def __init__(self) -> None:
        logging.Handler.__init__(self)

    @property
    def stream(self):
        return sys.stdout


def configure_logging() -> None:
    """Deja listo el logger de auditoría. Es idempotente."""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        handler = _StdoutHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # propagate se deja en True (su valor por defecto) para que otros handlers,
    # como el de caplog en los tests, también reciban los registros.