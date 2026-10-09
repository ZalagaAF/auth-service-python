from sqlalchemy.exc import IntegrityError

from app.core.exceptions import UserAlreadyExistsError
from app.core.security import hash_password
from app.models import User
from app.repositories.user_repository import UserRepository


class AuthService():

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def register(self, username: str, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        hashed_password = hash_password(password)

        try:
            user = self.repository.create(username, normalized_email, hashed_password)
        except IntegrityError:
            raise UserAlreadyExistsError
        
        return user