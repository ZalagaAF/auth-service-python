from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_user_repository, require_role
from app.core.roles import ROLE_ADMIN
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserPage, UserProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    # El perfil se arma acá, con la sesión todavía abierta: los roles se cargan
    # de forma perezosa al accederlos.
    return UserProfile.model_validate(current_user)

@router.get("", response_model=UserPage, dependencies=[Depends(require_role(ROLE_ADMIN))])
def list_users(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    repository: Annotated[UserRepository, Depends(get_user_repository)] = None,
):
    users = repository.list_paginated(limit=limit, offset=offset)
    total_count = repository.count()

    return UserPage(
        items=users,
        total=total_count,
        limit=limit,
        offset=offset,
    )