import pytest

from app.core.rate_limit import LOGIN_MAX_ATTEMPTS, LOGIN_RATE_LIMIT_WINDOW_SECONDS

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"
PASSWORD_INCORRECTA = "otra-clave-123"


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


def _agotar_los_intentos(client):
    """Hace LOGIN_MAX_ATTEMPTS intentos fallidos: todos deben dar 401, ninguno bloqueado."""
    for numero in range(1, LOGIN_MAX_ATTEMPTS + 1):
        respuesta = _login(client, password=PASSWORD_INCORRECTA)
        assert respuesta.status_code == 401, f"el intento {numero} no debería bloquearse"


def test_tras_agotar_los_intentos_el_siguiente_devuelve_429(client, usuario):
    _agotar_los_intentos(client)

    respuesta = _login(client, password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 429


def test_el_bloqueo_responde_con_detail_y_retry_after(client, usuario):
    _agotar_los_intentos(client)

    respuesta = _login(client, password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 429
    assert isinstance(respuesta.json()["detail"], str)
    assert 1 <= int(respuesta.headers["retry-after"]) <= LOGIN_RATE_LIMIT_WINDOW_SECONDS


def test_durante_el_bloqueo_ni_la_contrasena_correcta_permite_entrar(client, usuario):
    _agotar_los_intentos(client)

    respuesta = _login(client)  # credenciales correctas

    assert respuesta.status_code == 429
    assert "access_token" not in respuesta.json()


def test_los_intentos_exitosos_tambien_cuentan(client, usuario):
    for _ in range(LOGIN_MAX_ATTEMPTS):
        assert _login(client).status_code == 200

    assert _login(client).status_code == 429


def test_cambiar_el_email_no_evita_el_bloqueo(client, usuario):
    _agotar_los_intentos(client)

    respuesta = _login(client, email="otra@example.com", password=PASSWORD_INCORRECTA)

    assert respuesta.status_code == 429


def test_un_x_forwarded_for_falso_no_evita_el_bloqueo(client, usuario):
    _agotar_los_intentos(client)

    respuesta = _login(
        client,
        password=PASSWORD_INCORRECTA,
        headers={"X-Forwarded-For": "203.0.113.7"},
    )

    assert respuesta.status_code == 429


def test_el_limite_solo_afecta_a_login(client, usuario):
    _agotar_los_intentos(client)

    respuesta = client.post(REFRESH_URL, json={"refresh_token": "token-inexistente"})

    assert respuesta.status_code == 401  # su propio 401, no un 429