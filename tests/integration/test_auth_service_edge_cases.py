import pytest
from sqlalchemy import func, select

from app.core.exceptions import InvalidRefreshTokenError, InvalidTokenError
from app.models.refresh_tokens import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services import auth_service as auth_service_module
from app.services.auth_service import AuthService

pytestmark = pytest.mark.usefixtures("base_roles")


@pytest.fixture
def auth_service(db_session):
    return AuthService(
        UserRepository(db_session),
        RoleRepository(db_session),
        RefreshTokenRepository(db_session),
    )


def _activos(db_session):
    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    return db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.revoked_at.is_(None))
    )


def test_perder_la_carrera_al_rotar_se_trata_como_reutilizacion(
    auth_service, db_session, monkeypatch
):
    user = auth_service.register(
        username="ana", email="ana@example.com", password="Clave-segura-123"
    )
    token_de_la_carrera = auth_service.issue_refresh_token(user)
    auth_service.issue_refresh_token(user)  # otra sesión del mismo usuario
    assert _activos(db_session) == 2  # precondición
    # Simula que otro pedido ya usó el token: rotate() no pudo revocarlo
    monkeypatch.setattr(
        auth_service.refresh_token_repository, "rotate", lambda *args, **kwargs: None
    )

    with pytest.raises(InvalidRefreshTokenError):
        auth_service.refresh(token_de_la_carrera)

    assert _activos(db_session) == 0  # se cerraron todas las sesiones del usuario


def test_un_sub_que_no_es_texto_es_rechazado(auth_service, monkeypatch):
    monkeypatch.setattr(
        auth_service_module, "decode_access_token", lambda token: {"sub": 12345}
    )

    with pytest.raises(InvalidTokenError):
        auth_service.get_user_from_token("cualquier-cosa")