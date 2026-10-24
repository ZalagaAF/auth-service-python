import uuid

from typing import TYPE_CHECKING

from app.models.user_roles import user_roles

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.users import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")