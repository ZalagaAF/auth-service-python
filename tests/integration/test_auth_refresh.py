import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.security import (
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.refresh_tokens import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"
EMAIL = "ana@example.com"
CREDENCIALES = {"email": EMAIL, "password": "Clave-segura-123"}


@pytest.fixture
def sesion(client):
    """Registra a Ana, inicia sesión y devuelve su id junto con los tokens del login."""
    registro = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": CREDENCIALES["password"]},
    )
    assert registro.status_code == 201
    login = client.post(LOGIN_URL, json=CREDENCIALES)
    assert login.status_code == 200
    return {"user_id": registro.json()["id"], **login.json()}


def _refrescar(client, refresh_token):
    return client.post(REFRESH_URL, json={"refresh_token": refresh_token})


def _activos(db_session):
    return db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.revoked_at.is_(None))
    )


def test_refresh_devuelve_un_nuevo_par_de_tokens(client, sesion):
    # Sin cabecera Authorization: el access token puede estar vencido al refrescar.
    respuesta = _refrescar(client, sesion["refresh_token"])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["refresh_token"] != sesion["refresh_token"]
    assert decode_access_token(cuerpo["access_token"])["sub"] == sesion["user_id"]


def test_el_nuevo_access_token_sirve_en_me(client, sesion):
    respuesta = _refrescar(client, sesion["refresh_token"])
    assert respuesta.status_code == 200

    me = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {respuesta.json()['access_token']}"},
    )

    assert me.status_code == 200
    assert me.json()["id"] == sesion["user_id"]


def test_el_token_usado_queda_revocado_y_el_nuevo_queda_activo(
    client, db_session, sesion
):
    respuesta = _refrescar(client, sesion["refresh_token"])
    assert respuesta.status_code == 200
    nuevo = respuesta.json()["refresh_token"]

    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    viejo_db = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(sesion["refresh_token"])
        )
    )
    nuevo_db = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(nuevo)
        )
    )
    assert viejo_db is not None and viejo_db.revoked_at is not None
    assert nuevo_db is not None and nuevo_db.revoked_at is None


def test_cada_refresh_rota_el_token(client, sesion):
    tokens = [sesion["refresh_token"]]
    for _ in range(3):
        respuesta = _refrescar(client, tokens[-1])
        assert respuesta.status_code == 200
        tokens.append(respuesta.json()["refresh_token"])

    assert len(set(tokens)) == 4


def test_reutilizar_un_refresh_token_ya_usado_devuelve_401(client, sesion):
    primero = _refrescar(client, sesion["refresh_token"])
    assert primero.status_code == 200  # control: la primera vez funciona

    segundo = _refrescar(client, sesion["refresh_token"])

    assert segundo.status_code == 401
    assert segundo.headers["www-authenticate"] == "Bearer"


def test_la_reutilizacion_revoca_todas_las_sesiones_del_usuario(
    client, db_session, sesion
):
    otro_dispositivo = client.post(LOGIN_URL, json=CREDENCIALES)
    assert otro_dispositivo.status_code == 200
    token_del_otro = otro_dispositivo.json()["refresh_token"]

    primero = _refrescar(client, sesion["refresh_token"])
    assert primero.status_code == 200
    token_nuevo = primero.json()["refresh_token"]

    assert _refrescar(client, sesion["refresh_token"]).status_code == 401  # reutilización
    assert _refrescar(client, token_nuevo).status_code == 401
    assert _refrescar(client, token_del_otro).status_code == 401
    db_session.expire_all()
    assert _activos(db_session) == 0


def test_un_refresh_token_desconocido_devuelve_401(client, sesion):
    respuesta = _refrescar(client, generate_refresh_token())

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_un_refresh_token_vencido_devuelve_401(client, db_session, sesion):
    repo = RefreshTokenRepository(db_session)
    user_id = uuid.UUID(sesion["user_id"])
    ahora = datetime.now(timezone.utc)
    vigente = generate_refresh_token()
    repo.create(
        user_id=user_id,
        token_hash=hash_refresh_token(vigente),
        expires_at=ahora + timedelta(minutes=5),
    )
    vencido = generate_refresh_token()
    repo.create(
        user_id=user_id,
        token_hash=hash_refresh_token(vencido),
        expires_at=ahora - timedelta(minutes=1),
    )

    assert _refrescar(client, vigente).status_code == 200  # control
    assert _refrescar(client, vencido).status_code == 401


def test_un_usuario_inactivo_no_puede_refrescar(client, db_session, sesion):
    usuario = UserRepository(db_session).get_by_email(EMAIL)
    usuario.is_active = False
    db_session.commit()

    respuesta = _refrescar(client, sesion["refresh_token"])

    assert respuesta.status_code == 401


def test_un_access_token_no_sirve_como_refresh_token(client, sesion):
    respuesta = _refrescar(client, sesion["access_token"])

    assert respuesta.status_code == 401


def test_un_refresh_token_no_sirve_como_access_token(client, sesion):
    respuesta = client.get(
        ME_URL, headers={"Authorization": f"Bearer {sesion['refresh_token']}"}
    )

    assert respuesta.status_code == 401


def test_todos_los_rechazos_devuelven_el_mismo_cuerpo(client, sesion):
    desconocido = _refrescar(client, generate_refresh_token())
    con_access_token = _refrescar(client, sesion["access_token"])
    assert _refrescar(client, sesion["refresh_token"]).status_code == 200
    reutilizado = _refrescar(client, sesion["refresh_token"])

    for respuesta in (desconocido, con_access_token, reutilizado):
        assert respuesta.status_code == 401
        assert respuesta.headers["www-authenticate"] == "Bearer"
    assert desconocido.json() == con_access_token.json() == reutilizado.json()


def test_sin_el_campo_refresh_token_devuelve_422(client):
    respuesta = client.post(REFRESH_URL, json={})

    assert respuesta.status_code == 422