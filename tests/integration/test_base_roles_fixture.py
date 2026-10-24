from sqlalchemy import select

from app.models.roles import Role


def test_base_roles_devuelve_un_rol_por_cada_nombre_base(base_roles):
    assert {nombre: rol.name for nombre, rol in base_roles.items()} == {
        "admin": "admin",
        "user": "user",
    }


def test_base_roles_entrega_los_roles_con_id_asignado(base_roles):
    # El id lo asigna Python al hacer flush: si el fixture no lo hace, queda en None.
    assert all(rol.id is not None for rol in base_roles.values())


def test_base_roles_los_deja_guardados_en_la_base(db_session, base_roles):
    nombres = db_session.scalars(select(Role.name).order_by(Role.name)).all()
    assert nombres == ["admin", "user"]