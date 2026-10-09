import pytest

from app.core.exceptions import InvalidCredentialsError
from app.repositories.user_repository import UserRepository
from app.services import auth_service as auth_service_module
from app.services.auth_service import AuthService

EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"


@pytest.fixture
def auth_service(db_session):
    return AuthService(UserRepository(db_session))


@pytest.fixture
def usuario_registrado(auth_service):
    return auth_service.register(username="ana", email=EMAIL, password=PASSWORD)


def test_authenticate_con_credenciales_validas_devuelve_el_usuario(
    auth_service, usuario_registrado
):
    user = auth_service.authenticate(email=EMAIL, password=PASSWORD)

    assert user.id == usuario_registrado.id


def test_authenticate_normaliza_el_email(auth_service, usuario_registrado):
    user = auth_service.authenticate(email="  ANA@Example.com ", password=PASSWORD)

    assert user.id == usuario_registrado.id


def test_authenticate_con_contrasena_incorrecta_lanza_invalid_credentials(
    auth_service, usuario_registrado
):
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(email=EMAIL, password="otra-clave-123")


def test_authenticate_con_email_inexistente_lanza_invalid_credentials(auth_service):
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(email="nadie@example.com", password=PASSWORD)


def test_authenticate_con_usuario_inactivo_lanza_invalid_credentials(
    auth_service, usuario_registrado, db_session
):
    usuario_registrado.is_active = False
    db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(email=EMAIL, password=PASSWORD)


def test_authenticate_con_email_inexistente_igual_verifica_un_hash(
    auth_service, monkeypatch
):
    llamadas = []
    original = auth_service_module.verify_password

    def espia(password, hashed_password):
        llamadas.append(hashed_password)
        return original(password, hashed_password)

    monkeypatch.setattr(auth_service_module, "verify_password", espia)

    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(email="nadie@example.com", password=PASSWORD)

    assert len(llamadas) == 1