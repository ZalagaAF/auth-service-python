import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime


class UserProfile(UserRead):
    roles: list[str]

    @field_validator("roles", mode="before")
    @classmethod
    def roles_a_nombres(cls, roles: list[Any]) -> list[str]:
        nombres = [rol if isinstance(rol, str) else rol.name for rol in roles]
        return sorted(nombres)