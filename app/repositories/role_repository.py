from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role


class RoleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(self, name: str) -> Role | None:
        consulta = select(Role).where(Role.name == name)
        return self.session.scalar(consulta)