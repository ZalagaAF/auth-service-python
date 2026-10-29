import pytest

from app.core.roles import ROLE_ADMIN, ROLE_USER
from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.usefixtures("base_roles")

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/users/me"
RUTA_VIEJA = "/api/v1/auth/me"
EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"


@pytest.fixture
def crear_usuario(db_session, base_roles):
    def _crear(nombre, roles):
        return UserRepository(db_session).create(
            username=nombre,
            email=f"{nombre}@example.com",
            hashed_password="hash-de-prueba",
            roles=[base_roles[rol] for rol in roles],
        )

    return _crear


def _cabeceras(usuario):
    token = create_access_token(subject=str(usuario.id))
    return {"Authorization": f"Bearer {token}"}


def test_me_devuelve_el_perfil_del_usuario_con_sus_roles(client):
    registro = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": PASSWORD},
    )
    assert registro.status_code == 201
    login = client.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 200

    respuesta = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"id", "username", "email", "is_active", "created_at", "roles"}
    assert cuerpo["id"] == registro.json()["id"]
    assert cuerpo["roles"] == ["user"]


def test_me_de_un_admin_lista_sus_roles_ordenados(client, crear_usuario):
    usuario = crear_usuario("beto", [ROLE_USER, ROLE_ADMIN])

    respuesta = client.get(ME_URL, headers=_cabeceras(usuario))

    assert respuesta.status_code == 200
    assert respuesta.json()["roles"] == ["admin", "user"]


def test_me_refleja_los_cambios_de_rol_con_el_mismo_token(
    client, db_session, base_roles, crear_usuario
):
    usuario = crear_usuario("beto", [ROLE_USER])
    cabeceras = _cabeceras(usuario)
    antes = client.get(ME_URL, headers=cabeceras)
    assert antes.status_code == 200
    assert antes.json()["roles"] == ["user"]  # control

    usuario.roles.append(base_roles[ROLE_ADMIN])
    db_session.commit()

    despues = client.get(ME_URL, headers=cabeceras)
    assert despues.status_code == 200
    assert despues.json()["roles"] == ["admin", "user"]


def test_me_sin_token_devuelve_401(client):
    respuesta = client.get(ME_URL)

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_me_con_un_token_invalido_devuelve_401(client):
    respuesta = client.get(ME_URL, headers={"Authorization": "Bearer esto.no.es-un-jwt"})

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_la_ruta_vieja_auth_me_ya_no_existe(client, crear_usuario):
    usuario = crear_usuario("beto", [ROLE_USER])

    respuesta = client.get(RUTA_VIEJA, headers=_cabeceras(usuario))

    assert respuesta.status_code == 404