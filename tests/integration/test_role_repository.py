from app.repositories.role_repository import RoleRepository


def test_get_by_name_devuelve_el_rol_pedido(db_session, base_roles):
    repo = RoleRepository(db_session)  

    admin = repo.get_by_name("admin")
    usuario = repo.get_by_name("user")

    assert admin is not None and admin.name == "admin"
    assert usuario is not None and usuario.name == "user"
    assert admin.id == base_roles["admin"].id
    assert usuario.id == base_roles["user"].id


def test_get_by_name_devuelve_none_si_el_rol_no_existe(db_session, base_roles):
    # base_roles evita que el None se deba a una tabla vacía
    assert RoleRepository(db_session).get_by_name("superadmin") is None


def test_get_by_name_distingue_mayusculas_de_minusculas(db_session, base_roles):
    assert RoleRepository(db_session).get_by_name("ADMIN") is None