import pytest
from sqlalchemy import func, select

from app.core.security import generate_refresh_token, hash_refresh_token
from app.models.refresh_tokens import RefreshToken

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
EMAIL = "ana@example.com"
CREDENCIALES = {"email": EMAIL, "password": "Clave-segura-123"}


@pytest.fixture
def sesion(client):
    """Registra a Ana, inicia sesión y devuelve los tokens del login."""
    registro = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": CREDENCIALES["password"]},
    )
    assert registro.status_code == 201
    login = client.post(LOGIN_URL, json=CREDENCIALES)
    assert login.status_code == 200
    return login.json()


def _logout(client, refresh_token):
    return client.post(LOGOUT_URL, json={"refresh_token": refresh_token})


def _refrescar(client, refresh_token):
    return client.post(REFRESH_URL, json={"refresh_token": refresh_token})


def _activos(db_session):
    return db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.revoked_at.is_(None))
    )


def test_el_logout_devuelve_204_sin_cuerpo(client, sesion):
    # Sin cabecera Authorization: el access token puede estar vencido al cerrar sesión.
    respuesta = _logout(client, sesion["refresh_token"])

    assert respuesta.status_code == 204
    assert respuesta.content == b""


def test_el_logout_revoca_el_refresh_token_en_la_base(client, db_session, sesion):
    respuesta = _logout(client, sesion["refresh_token"])
    assert respuesta.status_code == 204

    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    fila = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(sesion["refresh_token"])
        )
    )
    assert fila is not None
    assert fila.revoked_at is not None


def test_despues_del_logout_el_refresh_token_ya_no_sirve(client, sesion):
    assert _logout(client, sesion["refresh_token"]).status_code == 204

    respuesta = _refrescar(client, sesion["refresh_token"])

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_el_logout_solo_cierra_la_sesion_indicada(client, sesion):
    otro_dispositivo = client.post(LOGIN_URL, json=CREDENCIALES)
    assert otro_dispositivo.status_code == 200

    assert _logout(client, sesion["refresh_token"]).status_code == 204

    # La sesión del otro dispositivo sigue viva
    otro = _refrescar(client, otro_dispositivo.json()["refresh_token"])
    assert otro.status_code == 200


def test_repetir_el_logout_devuelve_204_y_no_cierra_otras_sesiones(client, sesion):
    otro_dispositivo = client.post(LOGIN_URL, json=CREDENCIALES)
    assert otro_dispositivo.status_code == 200

    primero = _logout(client, sesion["refresh_token"])
    segundo = _logout(client, sesion["refresh_token"])

    assert primero.status_code == 204
    assert segundo.status_code == 204
    # Un logout repetido no es una "reutilización": la otra sesión sigue viva
    otro = _refrescar(client, otro_dispositivo.json()["refresh_token"])
    assert otro.status_code == 200


def test_logout_con_un_token_desconocido_devuelve_204_y_no_toca_nada(
    client, db_session, sesion
):
    respuesta = _logout(client, generate_refresh_token())

    assert respuesta.status_code == 204
    db_session.expire_all()
    assert _activos(db_session) == 1  # el token de la sesión sigue activo


def test_logout_con_un_access_token_devuelve_204_y_no_revoca_nada(
    client, db_session, sesion
):
    respuesta = _logout(client, sesion["access_token"])

    assert respuesta.status_code == 204
    db_session.expire_all()
    assert _activos(db_session) == 1


def test_logout_sin_el_campo_refresh_token_devuelve_422(client):
    respuesta = client.post(LOGOUT_URL, json={})

    assert respuesta.status_code == 422