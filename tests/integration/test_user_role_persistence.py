import uuid

import pytest
from sqlalchemy import delete, func, insert, select
from sqlalchemy.exc import IntegrityError

from app.models.roles import Role
from app.models.user_roles import user_roles
from app.models.users import User


def _crear_usuario(db_session, sufijo="a"):
    usuario = User(
        username=f"usuario_{sufijo}",
        email=f"{sufijo}@example.com",
        hashed_password="hash-de-prueba",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _contar(db_session, tabla):
    return db_session.scalar(select(func.count()).select_from(tabla))


def test_se_puede_guardar_y_leer_un_rol(db_session):
    rol = Role(name="editor")
    db_session.add(rol)
    db_session.flush()
    rol_id = rol.id
    assert isinstance(rol_id, uuid.UUID)

    db_session.expire_all()  # fuerza a leer de la base y no de memoria
    leido = db_session.scalar(select(Role).where(Role.name == "editor"))
    assert leido is not None
    assert leido.id == rol_id


def test_no_se_pueden_crear_dos_roles_con_el_mismo_nombre(db_session):
    db_session.add(Role(name="editor"))
    db_session.flush()

    db_session.add(Role(name="editor"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_un_rol_sin_nombre_es_rechazado(db_session):
    db_session.add(Role(name=None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_asignar_un_rol_inserta_una_fila_en_user_roles(db_session):
    usuario = _crear_usuario(db_session)
    rol = Role(name="editor")
    usuario.roles.append(rol)
    db_session.flush()

    filas = db_session.execute(
        select(user_roles.c.user_id, user_roles.c.role_id).where(
            user_roles.c.user_id == usuario.id
        )
    ).all()
    assert [tuple(f) for f in filas] == [(usuario.id, rol.id)]


def test_la_relacion_se_lee_desde_ambos_lados(db_session):
    usuario = _crear_usuario(db_session)
    rol = Role(name="editor")
    usuario.roles.append(rol)
    db_session.flush()
    db_session.expire_all()  # sin esto, la lista en memoria pasaría el test sin tocar la base

    assert [r.name for r in usuario.roles] == ["editor"]
    assert [u.id for u in rol.users] == [usuario.id]


def test_un_usuario_puede_tener_varios_roles_y_un_rol_varios_usuarios(db_session):
    ana = _crear_usuario(db_session, "ana")
    beto = _crear_usuario(db_session, "beto")
    editor = Role(name="editor")
    auditor = Role(name="auditor")
    ana.roles.extend([editor, auditor])
    beto.roles.append(editor)
    db_session.flush()
    db_session.expire_all()

    assert {r.name for r in ana.roles} == {"editor", "auditor"}
    assert {r.name for r in beto.roles} == {"editor"}
    assert {u.id for u in editor.users} == {ana.id, beto.id}
    assert {u.id for u in auditor.users} == {ana.id}


def test_no_se_puede_repetir_el_mismo_par_usuario_rol(db_session):
    usuario = _crear_usuario(db_session)
    rol = Role(name="editor")
    db_session.add(rol)
    db_session.flush()
    fila = {"user_id": usuario.id, "role_id": rol.id}
    db_session.execute(insert(user_roles).values(**fila))  # la primera inserción es válida

    with pytest.raises(IntegrityError):
        db_session.execute(insert(user_roles).values(**fila))


def test_borrar_un_usuario_borra_sus_filas_de_user_roles_pero_no_el_rol(db_session):
    usuario = _crear_usuario(db_session)
    rol = Role(name="editor")
    usuario.roles.append(rol)
    db_session.flush()
    assert _contar(db_session, user_roles) == 1  # precondición

    # DELETE de Core (sin cascadas del ORM): tiene que ser la base quien aplique ON DELETE CASCADE
    db_session.execute(delete(User).where(User.id == usuario.id))

    assert _contar(db_session, user_roles) == 0
    roles_restantes = db_session.scalar(
        select(func.count()).select_from(Role).where(Role.id == rol.id)
    )
    assert roles_restantes == 1


def test_borrar_un_rol_borra_sus_filas_de_user_roles_pero_no_al_usuario(db_session):
    usuario = _crear_usuario(db_session)
    rol = Role(name="editor")
    usuario.roles.append(rol)
    db_session.flush()
    assert _contar(db_session, user_roles) == 1  # precondición

    db_session.execute(delete(Role).where(Role.id == rol.id))

    assert _contar(db_session, user_roles) == 0
    usuarios_restantes = db_session.scalar(
        select(func.count()).select_from(User).where(User.id == usuario.id)
    )
    assert usuarios_restantes == 1