from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTokenError
from app.db.session import get_db
from app.models import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

# auto_error=False: el 401 lo armamos nosotros, para que sea idéntico en todos los casos.
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(
        UserRepository(db),
        RoleRepository(db),
        RefreshTokenRepository(db),
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    if credentials is None:
        raise _unauthorized()

    try:
        return service.get_user_from_token(credentials.credentials)
    except InvalidTokenError:
        raise _unauthorized() from None


def require_role(*role_names: str) -> Callable[..., User]:
    if not role_names or any(not nombre.strip() for nombre in role_names):
        raise ValueError(
            "require_role necesita al menos un nombre de rol y ninguno puede estar vacío."
        )

    required_roles = frozenset(role_names)

    def check_role(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        user_roles = {role.name for role in current_user.roles}
        if user_roles.isdisjoint(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta acción.",
            )
        return current_user

    return check_role

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)