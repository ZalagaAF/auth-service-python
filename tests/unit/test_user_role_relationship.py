from sqlalchemy import inspect as sa_inspect

from app.models.roles import Role
from app.models.user_roles import user_roles
from app.models.users import User


def test_user_tiene_relacion_roles_hacia_role():
    rel = sa_inspect(User).relationships["roles"]
    assert rel.mapper.class_ is Role


def test_user_roles_usa_la_tabla_intermedia():
    rel = sa_inspect(User).relationships["roles"]
    assert rel.secondary is user_roles


def test_user_roles_es_una_coleccion():
    rel = sa_inspect(User).relationships["roles"]
    assert rel.uselist is True


def test_role_tiene_relacion_users_hacia_user():
    rel = sa_inspect(Role).relationships["users"]
    assert rel.mapper.class_ is User
    assert rel.secondary is user_roles
    assert rel.uselist is True


def test_las_relaciones_son_bidireccionales():
    assert sa_inspect(User).relationships["roles"].back_populates == "users"
    assert sa_inspect(Role).relationships["users"].back_populates == "roles"


def test_un_usuario_nuevo_tiene_la_lista_de_roles_vacia():
    usuario = User(username="ana", email="ana@example.com", hashed_password="hash-de-prueba")
    assert usuario.roles == []