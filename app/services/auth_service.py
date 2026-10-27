import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.exceptions import (
    DefaultRoleNotFoundError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.roles import ROLE_USER
from app.core.security import (
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

# Hash de una contraseña descartable. Se usa cuando el email no existe, para que
# el login tarde lo mismo exista o no la cuenta (evita ataques de tiempo).
_DUMMY_HASH = hash_password("contrasena-descartable")


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        role_repository: RoleRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self.repository = repository
        self.role_repository = role_repository
        self.refresh_token_repository = refresh_token_repository

    def register(self, username: str, email: str, password: str) -> User:
        # Primero el rol: si no existe, falla antes de escribir nada y antes
        # de gastar el hash de Argon2.
        default_role = self.role_repository.get_by_name(ROLE_USER)
        if default_role is None:
            raise DefaultRoleNotFoundError(ROLE_USER)

        normalized_email = email.strip().lower()
        hashed_password = hash_password(password)

        try:
            return self.repository.create(
                username=username,
                email=normalized_email,
                hashed_password=hashed_password,
                roles=[default_role],
            )
        except IntegrityError as exc:
            raise UserAlreadyExistsError from exc

    def authenticate(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        user = self.repository.get_by_email(normalized_email)

        hashed_password = user.hashed_password if user is not None else _DUMMY_HASH
        password_is_valid = verify_password(password, hashed_password)

        if user is None or not password_is_valid or not user.is_active:
            raise InvalidCredentialsError

        return user

    def get_user_from_token(self, token: str) -> User:
        # decode_access_token ya lanza InvalidTokenError si el token está mal
        # formado, vencido, firmado con otra clave o sin "exp" / "sub".
        claims = decode_access_token(token)

        subject = claims.get("sub")
        if not isinstance(subject, str):
            raise InvalidTokenError

        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            raise InvalidTokenError from exc

        user = self.repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError

        return user

    def issue_refresh_token(self, user: User) -> str:
        """Crea un refresh token para el usuario y devuelve el token en claro.

        En la base se guarda solo el hash: el token en claro se entrega una vez.
        """
        raw_token = generate_refresh_token()
        self.refresh_token_repository.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=self._refresh_token_expiry(),
        )
        return raw_token

    def refresh(self, refresh_token: str) -> tuple[User, str]:
        """Rota un refresh token: revoca el usado y emite uno nuevo.

        Devuelve el usuario y el refresh token nuevo en claro.
        """
        token = self.refresh_token_repository.get_by_hash(
            hash_refresh_token(refresh_token)
        )
        if token is None:
            raise InvalidRefreshTokenError

        user_id = token.user_id

        if token.revoked_at is not None:
            # Reutilización: alguien está repitiendo un token ya usado. Se cierran
            # todas las sesiones del usuario. El repositorio hace commit antes de
            # que se lance la excepción, así el rollback del request no la deshace.
            self.refresh_token_repository.revoke_all_for_user(user_id)
            raise InvalidRefreshTokenError

        if token.expires_at <= datetime.now(timezone.utc):
            # Vencer es normal: se rechaza sin revocar las demás sesiones.
            raise InvalidRefreshTokenError

        user = self.repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        new_raw_token = generate_refresh_token()
        rotated = self.refresh_token_repository.rotate(
            token,
            hash_refresh_token(new_raw_token),
            self._refresh_token_expiry(),
        )
        if rotated is None:
            # Otro request usó el mismo token en el mismo instante: se trata
            # como reutilización.
            self.refresh_token_repository.revoke_all_for_user(user_id)
            raise InvalidRefreshTokenError

        return user, new_raw_token

    def logout(self, refresh_token: str) -> None:
        """Revoca el refresh token indicado.

        Es idempotente y no informa si el token existía o no: el resultado se
        ignora a propósito para que la respuesta sea siempre la misma.
        """
        self.refresh_token_repository.revoke_by_hash(
            hash_refresh_token(refresh_token)
        )

    @staticmethod
    def _refresh_token_expiry() -> datetime:
        days = get_settings().refresh_token_expire_days
        return datetime.now(timezone.utc) + timedelta(days=days)