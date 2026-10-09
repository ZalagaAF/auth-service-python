import pytest

from app.core.exceptions import UserAlreadyExistsError
from app.core.security import verify_password
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

PASSWORD = "Clave-segura-123"


@pytest.fixture
def auth_service(db_session):
    return AuthService(UserRepository(db_session))


def test_register_devuelve_el_usuario_creado(auth_service):
    user = auth_service.register(
        username="ana", email="ana@example.com", password=PASSWORD
    )

    assert user.username == "ana"
    assert user.email == "ana@example.com"
    assert user.is_active is True


def test_register_guarda_la_contrasena_hasheada(auth_service):
    user = auth_service.register(
        username="ana", email="ana@example.com", password=PASSWORD
    )

    assert user.hashed_password != PASSWORD
    assert verify_password(PASSWORD, user.hashed_password) is True


def test_register_normaliza_el_email(auth_service):
    user = auth_service.register(
        username="ana", email="  ANA@Example.com ", password=PASSWORD
    )

    assert user.email == "ana@example.com"


def test_register_con_email_duplicado_lanza_user_already_exists(auth_service):
    auth_service.register(username="ana", email="ana@example.com", password=PASSWORD)

    with pytest.raises(UserAlreadyExistsError):
        auth_service.register(
            username="otra", email="ana@example.com", password=PASSWORD
        )


def test_register_con_username_duplicado_lanza_user_already_exists(auth_service):
    auth_service.register(username="ana", email="ana@example.com", password=PASSWORD)

    with pytest.raises(UserAlreadyExistsError):
        auth_service.register(
            username="ana", email="otra@example.com", password=PASSWORD
        )


def test_register_con_email_duplicado_en_otras_mayusculas_lanza_user_already_exists(
    auth_service,
):
    auth_service.register(username="ana", email="ana@example.com", password=PASSWORD)

    with pytest.raises(UserAlreadyExistsError):
        auth_service.register(
            username="otra", email="ANA@EXAMPLE.COM", password=PASSWORD
        )