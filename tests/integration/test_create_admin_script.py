import pytest
from sqlalchemy import func, select

from app.core.exceptions import RoleNotFoundError, UserNotFoundError
from app.core.roles import ROLE_USER
from app.models.user_roles import user_roles
from app.repositories.user_repository import UserRepository
from app.scripts.create_admin import promote_to_admin, run

EMAIL = "ana@example.com"


@pytest.fixture
def ana(db_session, base_roles):
    return UserRepository(db_session).create(
        username="ana",
        email=EMAIL,
        hashed_password="hash-de-prueba",
        roles=[base_roles[ROLE_USER]],
    )


def _roles_de(db_session, usuario):
    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    return sorted(rol.name for rol in usuario.roles)


def test_promote_to_admin_agrega_admin_y_conserva_user(db_session, ana):
    resultado = promote_to_admin(db_session, EMAIL)

    assert resultado is True
    assert _roles_de(db_session, ana) == ["admin", "user"]


def test_promote_to_admin_es_idempotente(db_session, ana):
    assert promote_to_admin(db_session, EMAIL) is True  # control: la primera vez cambia

    segunda = promote_to_admin(db_session, EMAIL)

    assert segunda is False
    assert _roles_de(db_session, ana) == ["admin", "user"]
    filas = db_session.scalar(
        select(func.count()).select_from(user_roles).where(user_roles.c.user_id == ana.id)
    )
    assert filas == 2  # sin filas duplicadas


def test_promote_to_admin_normaliza_el_email(db_session, ana):
    resultado = promote_to_admin(db_session, "  ANA@Example.com ")

    assert resultado is True
    assert "admin" in _roles_de(db_session, ana)


def test_promote_to_admin_con_un_usuario_inexistente_lanza_user_not_found(
    db_session, ana
):
    with pytest.raises(UserNotFoundError):
        promote_to_admin(db_session, "nadie@example.com")

    assert _roles_de(db_session, ana) == ["user"]  # nadie fue promovido


def test_promote_to_admin_sin_el_rol_admin_sembrado_lanza_role_not_found(db_session):
    # Sin base_roles: la tabla roles está vacía
    UserRepository(db_session).create(
        username="ana", email=EMAIL, hashed_password="hash-de-prueba"
    )

    with pytest.raises(RoleNotFoundError):
        promote_to_admin(db_session, EMAIL)


def test_run_promueve_devuelve_0_e_informa(db_session, ana, capsys):
    codigo = run(EMAIL, db_session)

    assert codigo == 0
    assert EMAIL in capsys.readouterr().out
    assert "admin" in _roles_de(db_session, ana)


def test_run_sobre_alguien_que_ya_es_admin_devuelve_0(db_session, ana, capsys):
    assert run(EMAIL, db_session) == 0
    capsys.readouterr()  # descarta la salida de la primera vez

    codigo = run(EMAIL, db_session)

    assert codigo == 0
    assert capsys.readouterr().out != ""


def test_run_con_un_usuario_inexistente_devuelve_1_y_explica_el_error(
    db_session, base_roles, capsys
):
    codigo = run("nadie@example.com", db_session)

    assert codigo == 1
    assert capsys.readouterr().err != ""

def test_run_sin_el_rol_admin_sembrado_devuelve_1_y_sugiere_las_migraciones(
    db_session, capsys
):
    # Sin base_roles: la tabla roles está vacía
    UserRepository(db_session).create(
        username="ana", email=EMAIL, hashed_password="hash-de-prueba"
    )

    codigo = run(EMAIL, db_session)

    assert codigo == 1
    assert "alembic upgrade head" in capsys.readouterr().err