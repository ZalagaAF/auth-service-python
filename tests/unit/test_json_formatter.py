import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.logging_config import AUDIT_LOGGER_NAME, JsonFormatter, configure_logging


def _registro(mensaje="Login fallido", nivel=logging.WARNING, **extra):
    registro = logging.LogRecord(
        name=AUDIT_LOGGER_NAME,
        level=nivel,
        pathname=__file__,
        lineno=1,
        msg=mensaje,
        args=(),
        exc_info=None,
    )
    for clave, valor in extra.items():
        setattr(registro, clave, valor)
    return registro


@pytest.fixture
def audit_logger():
    """Deja el logger de auditoría como estaba al terminar cada test."""
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    handlers, nivel, propaga = list(logger.handlers), logger.level, logger.propagate
    logger.handlers = []
    yield logger
    logger.handlers = handlers
    logger.setLevel(nivel)
    logger.propagate = propaga


def test_la_salida_es_una_sola_linea_de_json_valido():
    salida = JsonFormatter().format(_registro())

    assert "\n" not in salida
    assert isinstance(json.loads(salida), dict)


def test_incluye_nivel_logger_y_mensaje():
    datos = json.loads(JsonFormatter().format(_registro("Login fallido")))

    assert datos["level"] == "WARNING"
    assert datos["logger"] == AUDIT_LOGGER_NAME
    assert datos["message"] == "Login fallido"


def test_incluye_un_timestamp_iso_en_utc():
    datos = json.loads(JsonFormatter().format(_registro()))

    momento = datetime.fromisoformat(datos["timestamp"])
    assert momento.utcoffset() == timedelta(0)
    assert abs(datetime.now(timezone.utc) - momento) < timedelta(seconds=10)


def test_incluye_los_campos_extra():
    registro = _registro(event="login_failed", client_ip="203.0.113.7")

    datos = json.loads(JsonFormatter().format(registro))

    assert datos["event"] == "login_failed"
    assert datos["client_ip"] == "203.0.113.7"


def test_los_valores_no_serializables_se_convierten_a_texto():
    identificador = uuid.uuid4()

    datos = json.loads(JsonFormatter().format(_registro(user_id=identificador)))

    assert datos["user_id"] == str(identificador)


def test_un_salto_de_linea_en_un_valor_no_rompe_el_formato():
    registro = _registro(email_hash="abc\n{\"level\": \"INFO\"}")

    salida = JsonFormatter().format(registro)

    assert "\n" not in salida  # no se puede inyectar una línea falsa
    assert json.loads(salida)["email_hash"] == "abc\n{\"level\": \"INFO\"}"


def test_no_incluye_los_atributos_internos_del_registro():
    datos = json.loads(JsonFormatter().format(_registro(event="login_failed")))

    for interno in ("args", "msg", "pathname", "lineno", "levelname", "created"):
        assert interno not in datos


def test_configure_logging_agrega_un_unico_handler_json_aunque_se_llame_dos_veces(
    audit_logger,
):
    configure_logging()
    configure_logging()

    assert len(audit_logger.handlers) == 1
    assert isinstance(audit_logger.handlers[0].formatter, JsonFormatter)


def test_configure_logging_deja_nivel_info_y_la_propagacion_activa(audit_logger):
    configure_logging()

    assert audit_logger.level == logging.INFO
    assert audit_logger.propagate is True