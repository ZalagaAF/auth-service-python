import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/users/me"
EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"
CLAVE_AJENA = "una-clave-que-no-es-la-del-servidor-0123456789"

CASOS_INVALIDOS = [
    "sin_cabecera",
    "esquema_basic",
    "bearer_sin_token",
    "token_basura",
    "firmado_con_otra_clave",
    "expirado",
    "sin_sub",
    "sub_no_uuid",
    "usuario_inexistente",
    "alg_none",
]


@pytest.fixture
def usuario(client):
    respuesta = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": PASSWORD},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


@pytest.fixture
def token(client, usuario):
    respuesta = client.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
    assert respuesta.status_code == 200
    return respuesta.json()["access_token"]


def _firmar(claims, clave=None):
    settings = get_settings()
    return jwt.encode(
        claims, clave or settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def _base64url(datos):
    crudo = json.dumps(datos).encode()
    return base64.urlsafe_b64encode(crudo).rstrip(b"=").decode()


def _cabeceras(caso, usuario_id):
    ahora = datetime.now(timezone.utc)
    vigentes = {"sub": usuario_id, "exp": ahora + timedelta(minutes=5)}

    if caso == "sin_cabecera":
        return {}
    if caso == "esquema_basic":
        return {"Authorization": "Basic YW5hOmNsYXZl"}
    if caso == "bearer_sin_token":
        return {"Authorization": "Bearer "}
    if caso == "token_basura":
        return {"Authorization": "Bearer esto.no.es-un-jwt"}

    if caso == "valido":
        token = _firmar(vigentes)
    elif caso == "firmado_con_otra_clave":
        token = _firmar(vigentes, CLAVE_AJENA)
    elif caso == "expirado":
        token = _firmar({**vigentes, "exp": ahora - timedelta(minutes=1)})
    elif caso == "sin_sub":
        token = _firmar({"exp": vigentes["exp"]})
    elif caso == "sub_no_uuid":
        token = _firmar({**vigentes, "sub": "esto-no-es-un-uuid"})
    elif caso == "usuario_inexistente":
        token = _firmar({**vigentes, "sub": str(uuid.uuid4())})
    elif caso == "alg_none":
        # Token sin firma: la tercera parte va vacía y el encabezado declara alg "none".
        claims = {"sub": usuario_id, "exp": int(vigentes["exp"].timestamp())}
        encabezado = {"alg": "none", "typ": "JWT"}
        token = f"{_base64url(encabezado)}.{_base64url(claims)}."
    else:
        raise ValueError(f"caso desconocido: {caso}")

    return {"Authorization": f"Bearer {token}"}


def test_me_con_token_valido_devuelve_el_usuario_autenticado(client, usuario, token):
    respuesta = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == usuario["id"]
    assert cuerpo["username"] == "ana"
    assert cuerpo["email"] == EMAIL
    assert "password" not in cuerpo
    assert "hashed_password" not in cuerpo


def test_un_token_armado_a_mano_con_claims_validos_es_aceptado(client, usuario):
    # Control positivo: demuestra que los tokens de _cabeceras son aceptables, así los
    # rechazos de abajo se deben a SU defecto y no a un claim que le falte al helper.
    respuesta = client.get(ME_URL, headers=_cabeceras("valido", usuario["id"]))

    assert respuesta.status_code == 200


@pytest.mark.parametrize("caso", CASOS_INVALIDOS)
def test_me_rechaza_con_401_toda_credencial_invalida(client, usuario, caso):
    respuesta = client.get(ME_URL, headers=_cabeceras(caso, usuario["id"]))

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_todos_los_rechazos_devuelven_el_mismo_cuerpo(client, usuario):
    cuerpos = []
    for caso in CASOS_INVALIDOS:
        respuesta = client.get(ME_URL, headers=_cabeceras(caso, usuario["id"]))
        assert respuesta.status_code == 401, caso
        cuerpos.append(respuesta.json())

    assert all(cuerpo == cuerpos[0] for cuerpo in cuerpos)


def test_un_usuario_desactivado_no_puede_usar_un_token_ya_emitido(
    client, db_session, usuario, token
):
    cabeceras = {"Authorization": f"Bearer {token}"}
    assert client.get(ME_URL, headers=cabeceras).status_code == 200  # control

    user = UserRepository(db_session).get_by_email(EMAIL)
    user.is_active = False
    db_session.commit()

    respuesta = client.get(ME_URL, headers=cabeceras)

    assert respuesta.status_code == 401