import pytest

from app.core.dependencies import require_role
from app.core.roles import ROLE_ADMIN, ROLE_USER


def test_require_role_sin_roles_lanza_value_error():
    with pytest.raises(ValueError):
        require_role()


@pytest.mark.parametrize("nombre", ["", "   "])
def test_require_role_con_un_nombre_vacio_lanza_value_error(nombre):
    with pytest.raises(ValueError):
        require_role(ROLE_ADMIN, nombre)


def test_require_role_con_roles_validos_devuelve_una_dependency_invocable():
    assert callable(require_role(ROLE_ADMIN))
    assert callable(require_role(ROLE_ADMIN, ROLE_USER))