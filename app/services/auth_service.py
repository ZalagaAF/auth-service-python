import uuid

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    DefaultRoleNotFoundError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.roles import ROLE_USER
from app.core.security import decode_access_token, hash_password, verify_password
from app.models import User
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
    ) -> None:
        self.repository = repository
        self.role_repository = role_repository

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