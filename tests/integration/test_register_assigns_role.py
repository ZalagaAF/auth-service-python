import pytest
from sqlalchemy import func, select

from app.core.exceptions import DefaultRoleNotFoundError
from app.models.roles import Role
from app.models.user_roles import user_roles
from app.models.users import User

URL_REGISTRO = "/api/v1/auth/register"  

def _payload(sufijo="ana", **extra):
    return {
        "username": f"usuario_{sufijo}",
        "email": f"{sufijo}@example.com",
        "password": "ClaveSegura123!",
        **extra,
    }


def _roles_de(db_session, email):
    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    usuario = db_session.scalar(select(User).where(User.email == email))
    assert usuario is not None
    return sorted(rol.name for rol in usuario.roles)


def test_el_registro_asigna_el_rol_user(client, db_session, base_roles):
    respuesta = client.post(URL_REGISTRO, json=_payload())

    assert respuesta.status_code == 201, respuesta.text
    assert _roles_de(db_session, "ana@example.com") == ["user"]


@pytest.mark.parametrize("campo", [{"role": "admin"}, {"roles": ["admin"]}])
def test_el_cliente_no_puede_elegir_su_rol_al_registrarse(
    client, db_session, base_roles, campo
):
    respuesta = client.post(URL_REGISTRO, json=_payload(**campo))

    assert respuesta.status_code == 201, respuesta.text
    assert _roles_de(db_session, "ana@example.com") == ["user"]


def test_registrar_varios_usuarios_no_duplica_roles(client, db_session, base_roles):
    for sufijo in ("ana", "beto"):
        respuesta = client.post(URL_REGISTRO, json=_payload(sufijo))
        assert respuesta.status_code == 201, respuesta.text

    assert _roles_de(db_session, "ana@example.com") == ["user"]
    assert _roles_de(db_session, "beto@example.com") == ["user"]
    assert db_session.scalar(select(func.count()).select_from(Role)) == 2
    assert db_session.scalar(select(func.count()).select_from(user_roles)) == 2


def test_sin_el_rol_user_sembrado_el_registro_falla_y_no_crea_el_usuario(
    client, db_session
):
    # Sin base_roles: la tabla roles está vacía
    with pytest.raises(DefaultRoleNotFoundError, match="user"):
        client.post(URL_REGISTRO, json=_payload())

    assert db_session.scalar(select(func.count()).select_from(User)) == 0