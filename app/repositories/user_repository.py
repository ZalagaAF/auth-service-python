import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.models import Role, User
from app.repositories.role_repository import RoleRepository


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        roles: list[Role] | None = None,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
        )
        if roles:
            user.roles = list(roles)
        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        consulta = select(User).where(User.email == email)
        return self.session.scalar(consulta)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        consulta = select(User).where(User.id == user_id)
        return self.session.scalar(consulta)

    def list_paginated(self, limit: int, offset: int) -> list[User]:
        consulta = (
            select(User)
            .options(selectinload(User.roles))
            .order_by(User.username)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(consulta).all())

    def count(self) -> int:
        consulta = select(func.count(User.id))
        return self.session.scalar(consulta) or 0