from contextlib import contextmanager

import pytest
from sqlalchemy import event

from app.core.roles import ROLE_ADMIN, ROLE_USER
from app.core.security import create_access_token
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.usefixtures("base_roles")

USERS_URL = "/api/v1/users"
ME_URL = "/api/v1/users/me"
CLAVES_DEL_PERFIL = {"id", "username", "email", "is_active", "created_at", "roles"}


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


@contextmanager
def _contar_selects(db_session):
    """Cuenta las consultas SELECT que se ejecutan dentro del bloque."""
    consultas = []
    conexion = db_session.get_bind()

    def registrar(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(conexion, "before_cursor_execute", registrar)
    try:
        yield consultas
    finally:
        event.remove(conexion, "before_cursor_execute", registrar)


def test_un_admin_lista_los_usuarios_con_el_formato_esperado(client, crear_usuario):
    admin = crear_usuario("ana", [ROLE_ADMIN, ROLE_USER])
    crear_usuario("beto", [ROLE_USER])

    respuesta = client.get(USERS_URL, headers=_cabeceras(admin))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"items", "total", "limit", "offset"}
    assert (cuerpo["total"], cuerpo["limit"], cuerpo["offset"]) == (2, 20, 0)
    assert len(cuerpo["items"]) == 2
    for item in cuerpo["items"]:
        assert set(item) == CLAVES_DEL_PERFIL
    assert "hashed_password" not in respuesta.text
    assert "hash-de-prueba" not in respuesta.text


def test_los_usuarios_vienen_ordenados_por_username(client, crear_usuario):
    admin = crear_usuario("zoe", [ROLE_ADMIN])
    for nombre in ("carla", "ana", "beto"):
        crear_usuario(nombre, [ROLE_USER])

    respuesta = client.get(USERS_URL, headers=_cabeceras(admin))

    assert respuesta.status_code == 200
    usernames = [item["username"] for item in respuesta.json()["items"]]
    assert usernames == ["ana", "beto", "carla", "zoe"]


def test_la_paginacion_respeta_limit_y_offset(client, crear_usuario):
    admin = crear_usuario("ana", [ROLE_ADMIN])
    for nombre in ("beto", "carla", "dario", "eva"):
        crear_usuario(nombre, [ROLE_USER])

    respuesta = client.get(
        USERS_URL, params={"limit": 2, "offset": 2}, headers=_cabeceras(admin)
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [item["username"] for item in cuerpo["items"]] == ["carla", "dario"]
    assert (cuerpo["total"], cuerpo["limit"], cuerpo["offset"]) == (5, 2, 2)


def test_cada_usuario_incluye_sus_roles(client, crear_usuario):
    admin = crear_usuario("ana", [ROLE_USER, ROLE_ADMIN])
    crear_usuario("beto", [ROLE_USER])
    crear_usuario("carla", [])

    respuesta = client.get(USERS_URL, headers=_cabeceras(admin))

    assert respuesta.status_code == 200
    roles = {item["username"]: item["roles"] for item in respuesta.json()["items"]}
    assert roles == {"ana": ["admin", "user"], "beto": ["user"], "carla": []}


def test_un_usuario_comun_recibe_403(client, crear_usuario):
    comun = crear_usuario("beto", [ROLE_USER])
    cabeceras = _cabeceras(comun)
    assert client.get(ME_URL, headers=cabeceras).status_code == 200  # control

    respuesta = client.get(USERS_URL, headers=cabeceras)

    assert respuesta.status_code == 403
    assert "www-authenticate" not in respuesta.headers
    assert "items" not in respuesta.json()


def test_sin_token_devuelve_401(client):
    respuesta = client.get(USERS_URL)

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_con_un_token_invalido_devuelve_401(client):
    respuesta = client.get(USERS_URL, headers={"Authorization": "Bearer esto.no.es-un-jwt"})

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"offset": -1}, {"limit": "abc"}],
)
def test_parametros_de_paginacion_invalidos_devuelven_422(
    client, crear_usuario, params
):
    admin = crear_usuario("ana", [ROLE_ADMIN])

    respuesta = client.get(USERS_URL, params=params, headers=_cabeceras(admin))

    assert respuesta.status_code == 422


def test_el_limite_maximo_permitido_es_100(client, crear_usuario):
    admin = crear_usuario("ana", [ROLE_ADMIN])

    respuesta = client.get(USERS_URL, params={"limit": 100}, headers=_cabeceras(admin))

    assert respuesta.status_code == 200
    assert respuesta.json()["limit"] == 100


def test_listar_usuarios_no_hace_una_consulta_por_cada_usuario(
    client, db_session, crear_usuario
):
    admin = crear_usuario("admin", [ROLE_ADMIN])
    for numero in range(10):
        crear_usuario(f"usuario{numero:02d}", [ROLE_USER])
    cabeceras = _cabeceras(admin)
    db_session.expire_all()  # nada cargado en memoria: cada dato sale de una consulta

    with _contar_selects(db_session) as consultas:
        respuesta = client.get(USERS_URL, params={"limit": 50}, headers=cabeceras)

    assert respuesta.status_code == 200
    assert len(respuesta.json()["items"]) == 11
    # Con selectinload son unas 6 consultas; con una por usuario serían más de 12.
    assert len(consultas) <= 8