from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.role_repository import RoleRepository
from app.services.auth_service import AuthService


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), RoleRepository(db))