"""create_admin.main: la línea de comandos que abre la sesión y sale con un código."""

import pytest

from app.core.roles import ROLE_USER
from app.repositories.user_repository import UserRepository
from app.scripts import create_admin
from app.scripts.create_admin import main

EMAIL = "ana@example.com"


@pytest.fixture
def usar_la_sesion_de_prueba(monkeypatch, db_session):
    """Hace que main() use la sesión de los tests y no la base de desarrollo."""

    def get_db_de_prueba():
        yield db_session

    monkeypatch.setattr(create_admin, "get_db", get_db_de_prueba)


@pytest.fixture
def ana(db_session, base_roles):
    return UserRepository(db_session).create(
        username="ana",
        email=EMAIL,
        hashed_password="hash-de-prueba",
        roles=[base_roles[ROLE_USER]],
    )


def test_main_promueve_al_usuario_y_sale_con_codigo_0(
    usar_la_sesion_de_prueba, db_session, ana, capsys
):
    with pytest.raises(SystemExit) as salida:
         main([EMAIL])

    assert salida.value.code == 0
    assert EMAIL in capsys.readouterr().out
    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    assert "admin" in {rol.name for rol in ana.roles}


def test_main_con_un_usuario_inexistente_sale_con_codigo_1(
    usar_la_sesion_de_prueba, base_roles, capsys
):
    with pytest.raises(SystemExit) as salida:
        main(["nadie@example.com"])

    assert salida.value.code == 1
    assert capsys.readouterr().err != ""


def test_main_sin_el_email_sale_con_codigo_2(capsys):
    with pytest.raises(SystemExit) as salida:
        main([])

    assert salida.value.code == 2  # argparse: error de uso