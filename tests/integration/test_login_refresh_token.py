import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import hash_refresh_token
from app.models.refresh_tokens import RefreshToken

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"


@pytest.fixture
def usuario(client):
    respuesta = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": PASSWORD},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def _login(client, password=PASSWORD):
    return client.post(LOGIN_URL, json={"email": EMAIL, "password": password})


def test_el_login_devuelve_un_refresh_token(client, usuario):
    respuesta = _login(client)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert isinstance(cuerpo["refresh_token"], str)
    assert len(cuerpo["refresh_token"]) >= 43
    assert cuerpo["refresh_token"] != cuerpo["access_token"]


def test_el_refresh_token_se_guarda_solo_como_hash(client, db_session, usuario):
    respuesta = _login(client)
    assert respuesta.status_code == 200
    crudo = respuesta.json()["refresh_token"]

    filas = db_session.scalars(select(RefreshToken)).all()

    assert len(filas) == 1
    assert filas[0].token_hash == hash_refresh_token(crudo)
    assert filas[0].token_hash != crudo
    assert filas[0].user_id == uuid.UUID(usuario["id"])
    assert filas[0].revoked_at is None


def test_el_refresh_token_vence_segun_la_configuracion(client, db_session, usuario):
    respuesta = _login(client)
    assert respuesta.status_code == 200

    fila = db_session.scalars(select(RefreshToken)).one()

    esperado = datetime.now(timezone.utc) + timedelta(
        days=get_settings().refresh_token_expire_days
    )
    assert abs(fila.expires_at - esperado) < timedelta(minutes=1)


def test_cada_login_emite_un_refresh_token_distinto(client, db_session, usuario):
    primero = _login(client)
    segundo = _login(client)

    assert primero.status_code == 200
    assert segundo.status_code == 200
    assert primero.json()["refresh_token"] != segundo.json()["refresh_token"]
    assert db_session.scalar(select(func.count()).select_from(RefreshToken)) == 2


def test_un_login_fallido_no_crea_refresh_tokens(client, db_session, usuario):
    respuesta = _login(client, password="otra-clave-123")

    assert respuesta.status_code == 401
    assert db_session.scalar(select(func.count()).select_from(RefreshToken)) == 0