from slowapi import Limiter

from app.core.rate_limit import (
    LOGIN_MAX_ATTEMPTS,
    LOGIN_RATE_LIMIT,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    limiter,
)


def test_el_login_permite_5_intentos_por_minuto():
    assert LOGIN_MAX_ATTEMPTS == 5
    assert LOGIN_RATE_LIMIT == "5/minute"


def test_la_ventana_del_limite_es_de_60_segundos():
    assert LOGIN_RATE_LIMIT_WINDOW_SECONDS == 60


def test_limiter_es_una_instancia_de_slowapi():
    assert isinstance(limiter, Limiter)