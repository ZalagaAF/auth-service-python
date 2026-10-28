import hashlib
import logging

import pytest

from app.core.logging_config import AUDIT_LOGGER_NAME
from app.core.rate_limit import LOGIN_MAX_ATTEMPTS

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"
PASSWORD_INCORRECTA = "otra-clave-123"
IP_DE_PRUEBA = "testclient"  


def _hash_esperado(email):
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16]


@pytest.fixture(autouse=True)
def capturar_auditoria(caplog):
    caplog.set_level(logging.INFO, logger=AUDIT_LOGGER_NAME)


@pytest.fixture
def usuario(client):
    respuesta = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": PASSWORD},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def _login(client, email=EMAIL, password=PASSWORD, headers=None):
    return client.post(
        LOGIN_URL, json={"email": email, "password": password}, headers=headers
    )


def _eventos(caplog):
    return [r for r in caplog.records if r.name == AUDIT_LOGGER_NAME]


def _todo_lo_registrado(caplog):
    """Texto de TODO lo capturado (de cualquier logger), para buscar datos sensibles."""
    return "\n".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)


def test_un_login_exitoso_registra_login_succeeded(client, caplog, usuario):
    respuesta = _login(client)

    assert respuesta.status_code == 200
    eventos = _eventos(caplog)
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.event == "login_succeeded"
    assert evento.levelno == logging.INFO
    assert evento.user_id == usuario["id"]
    assert evento.email_hash == _hash_esperado(EMAIL)
    assert evento.client_ip == IP_DE_PRUEBA


def test_un_login_fallido_registra_login_failed_como_warning(client, caplog, usuario):
    respuesta = _login(client, password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 401
    eventos = _eventos(caplog)
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.event == "login_failed"
    assert evento.levelno == logging.WARNING
    assert evento.email_hash == _hash_esperado(EMAIL)
    assert evento.client_ip == IP_DE_PRUEBA
    assert not hasattr(evento, "user_id")


def test_un_email_inexistente_tambien_registra_login_failed(client, caplog, usuario):
    respuesta = _login(client, email="nadie@example.com", password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 401
    eventos = _eventos(caplog)
    assert len(eventos) == 1
    assert eventos[0].event == "login_failed"
    assert eventos[0].email_hash == _hash_esperado("nadie@example.com")


def test_el_hash_del_email_ignora_las_mayusculas(client, caplog, usuario):
    respuesta = _login(client, email="ANA@Example.com", password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 401
    eventos = _eventos(caplog)
    assert len(eventos) == 1
    assert eventos[0].email_hash == _hash_esperado("ana@example.com")


def test_un_fallo_no_registra_ni_la_contrasena_ni_el_email(client, caplog, usuario):
    respuesta = _login(client, password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 401
    assert len(_eventos(caplog)) == 1  # precondición: sí se registró algo
    texto = _todo_lo_registrado(caplog)
    assert PASSWORD_INCORRECTA not in texto
    assert EMAIL not in texto


def test_un_exito_no_registra_contrasena_tokens_ni_email(client, caplog, usuario):
    respuesta = _login(client)

    assert respuesta.status_code == 200
    assert len(_eventos(caplog)) == 1  # precondición: sí se registró algo
    cuerpo = respuesta.json()
    texto = _todo_lo_registrado(caplog)
    assert PASSWORD not in texto
    assert cuerpo["access_token"] not in texto
    assert cuerpo["refresh_token"] not in texto
    assert EMAIL not in texto


def test_un_pedido_invalido_no_genera_eventos_ni_filtra_lo_escrito(
    client, caplog, usuario
):
    # Error típico: escribir la contraseña en el campo del email
    respuesta = _login(client, email=PASSWORD, password="x")

    assert respuesta.status_code == 422
    assert _eventos(caplog) == []
    assert PASSWORD not in _todo_lo_registrado(caplog)


def test_un_x_forwarded_for_falso_no_cambia_la_ip_registrada(client, caplog, usuario):
    respuesta = _login(
        client,
        password=PASSWORD_INCORRECTA,
        headers={"X-Forwarded-For": "203.0.113.7"},
    )

    assert respuesta.status_code == 401
    eventos = _eventos(caplog)
    assert len(eventos) == 1
    assert eventos[0].client_ip == IP_DE_PRUEBA


def test_el_bloqueo_por_rate_limit_registra_login_rate_limited(client, caplog, usuario):
    for _ in range(LOGIN_MAX_ATTEMPTS):
        assert _login(client, password=PASSWORD_INCORRECTA).status_code == 401

    bloqueado = _login(client, password=PASSWORD_INCORRECTA)

    assert bloqueado.status_code == 429
    eventos = _eventos(caplog)
    assert [e.event for e in eventos] == (
        ["login_failed"] * LOGIN_MAX_ATTEMPTS + ["login_rate_limited"]
    )
    ultimo = eventos[-1]
    assert ultimo.levelno == logging.WARNING
    assert ultimo.client_ip == IP_DE_PRUEBA
    assert ultimo.path == LOGIN_URL