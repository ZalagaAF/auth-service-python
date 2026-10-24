import pytest

from app.core.roles import BASE_ROLE_NAMES, ROLE_ADMIN, ROLE_USER


def test_nombres_de_los_roles_base():
    assert ROLE_ADMIN == "admin"
    assert ROLE_USER == "user"


def test_base_role_names_contiene_exactamente_admin_y_user_sin_repetidos():
    assert sorted(BASE_ROLE_NAMES) == ["admin", "user"]


def test_base_role_names_es_una_tupla_inmutable():
    assert isinstance(BASE_ROLE_NAMES, tuple)


@pytest.mark.parametrize("nombre", BASE_ROLE_NAMES)
def test_los_roles_base_cumplen_la_convencion_de_nombres(nombre):
    # minúsculas, sin espacios y dentro del largo de roles.name (String(50))
    assert nombre == nombre.strip().lower()
    assert " " not in nombre
    assert 0 < len(nombre) <= 50