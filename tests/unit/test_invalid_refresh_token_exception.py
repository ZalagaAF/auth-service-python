from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    UserAlreadyExistsError,
)


def test_invalid_refresh_token_error_es_una_excepcion():
    assert issubclass(InvalidRefreshTokenError, Exception)


def test_no_hereda_de_las_demas_excepciones_de_dominio():
    for otra in (InvalidCredentialsError, InvalidTokenError, UserAlreadyExistsError):
        assert not issubclass(InvalidRefreshTokenError, otra)