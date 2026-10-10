from sqlalchemy.exc import IntegrityError

from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository

# Hash de una contraseña descartable. Se usa cuando el email no existe, para que
# el login tarde lo mismo exista o no la cuenta (evita ataques de tiempo).
_DUMMY_HASH = hash_password("contrasena-descartable")


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def register(self, username: str, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        hashed_password = hash_password(password)

        try:
            return self.repository.create(
                username=username,
                email=normalized_email,
                hashed_password=hashed_password,
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
