import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.schemas.user import UserProfile


def _usuario(roles):
    return SimpleNamespace(
        id=uuid.uuid4(),
        username="ana",
        email="ana@example.com",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        hashed_password="hash-que-no-debe-salir",
        roles=[SimpleNamespace(name=nombre) for nombre in roles],
    )


def test_los_roles_se_convierten_en_nombres_ordenados():
    perfil = UserProfile.model_validate(_usuario(["user", "admin"]))

    assert perfil.roles == ["admin", "user"]


def test_un_usuario_sin_roles_tiene_una_lista_vacia():
    perfil = UserProfile.model_validate(_usuario([]))

    assert perfil.roles == []


def test_acepta_roles_que_ya_son_nombres():
    # FastAPI vuelve a validar la respuesta: los roles ya llegan como texto.
    perfil = UserProfile.model_validate(
        {
            "id": uuid.uuid4(),
            "username": "ana",
            "email": "ana@example.com",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "roles": ["user", "admin"],
        }
    )

    assert perfil.roles == ["admin", "user"]


def test_el_perfil_no_expone_la_contrasena_ni_su_hash():
    perfil = UserProfile.model_validate(_usuario(["user"]))

    datos = perfil.model_dump(mode="json")

    assert set(datos) == {"id", "username", "email", "is_active", "created_at", "roles"}
    assert "hash-que-no-debe-salir" not in str(datos)