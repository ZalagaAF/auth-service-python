from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import require_role
from app.core.roles import ROLE_ADMIN, ROLE_USER
from app.core.security import create_access_token
from app.db.session import get_db
from app.models import User
from app.repositories.user_repository import UserRepository


@pytest.fixture
def cliente(db_session):
    app = FastAPI()

    @app.get("/solo-admin")
    def solo_admin(usuario: Annotated[User, Depends(require_role(ROLE_ADMIN))]):
        return {"username": usuario.username}

    @app.get("/admin-o-user")
    def admin_o_user(
        usuario: Annotated[User, Depends(require_role(ROLE_ADMIN, ROLE_USER))],
    ):
        return {"username": usuario.username}

    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


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


def test_admin_accede_a_una_ruta_solo_admin(cliente, crear_usuario):
    admin = crear_usuario("ana", [ROLE_ADMIN])

    respuesta = cliente.get("/solo-admin", headers=_cabeceras(admin))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"username": "ana"}


def test_un_usuario_comun_recibe_403_en_una_ruta_solo_admin(cliente, crear_usuario):
    comun = crear_usuario("beto", [ROLE_USER])
    cabeceras = _cabeceras(comun)

    respuesta = cliente.get("/solo-admin", headers=cabeceras)

    assert respuesta.status_code == 403
    assert "www-authenticate" not in respuesta.headers
    assert "admin" not in respuesta.text.lower()  # no revela qué rol hacía falta
    # Control: su token es válido, lo único que le falta es el rol.
    assert cliente.get("/admin-o-user", headers=cabeceras).status_code == 200


def test_un_usuario_sin_roles_recibe_403(cliente, crear_usuario):
    sin_roles = crear_usuario("carla", [])

    respuesta = cliente.get("/solo-admin", headers=_cabeceras(sin_roles))

    assert respuesta.status_code == 403


def test_sin_token_devuelve_401_y_no_403(cliente):
    respuesta = cliente.get("/solo-admin")

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_token_invalido_devuelve_401_y_no_403(cliente):
    respuesta = cliente.get(
        "/solo-admin", headers={"Authorization": "Bearer esto.no.es-un-jwt"}
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("rol", [ROLE_ADMIN, ROLE_USER])
def test_ruta_con_varios_roles_acepta_a_cualquiera_de_ellos(
    cliente, crear_usuario, rol
):
    usuario = crear_usuario("ana", [rol])

    respuesta = cliente.get("/admin-o-user", headers=_cabeceras(usuario))

    assert respuesta.status_code == 200
    assert respuesta.json() == {"username": "ana"}


def test_ruta_con_varios_roles_rechaza_a_quien_no_tiene_ninguno(
    cliente, crear_usuario
):
    sin_roles = crear_usuario("carla", [])

    respuesta = cliente.get("/admin-o-user", headers=_cabeceras(sin_roles))

    assert respuesta.status_code == 403


def test_los_cambios_de_rol_se_aplican_con_el_mismo_token(
    cliente, db_session, base_roles, crear_usuario
):
    usuario = crear_usuario("ana", [ROLE_USER])
    cabeceras = _cabeceras(usuario)  # un único token para todo el test
    assert cliente.get("/solo-admin", headers=cabeceras).status_code == 403  # control

    usuario.roles.append(base_roles[ROLE_ADMIN])
    db_session.commit()
    assert cliente.get("/solo-admin", headers=cabeceras).status_code == 200

    usuario.roles.remove(base_roles[ROLE_ADMIN])
    db_session.commit()
    assert cliente.get("/solo-admin", headers=cabeceras).status_code == 403