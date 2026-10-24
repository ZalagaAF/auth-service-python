from app.core.exceptions import (
    DefaultRoleNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)


def test_default_role_not_found_error_es_una_excepcion():
    assert issubclass(DefaultRoleNotFoundError, Exception)


def test_no_hereda_de_las_excepciones_que_se_traducen_a_errores_del_cliente():
    for otra in (InvalidCredentialsError, InvalidTokenError, UserAlreadyExistsError):
        assert not issubclass(DefaultRoleNotFoundError, otra)