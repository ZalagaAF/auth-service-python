from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.user import UserProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    # El perfil se arma acá, con la sesión todavía abierta: los roles se cargan
    # de forma perezosa al accederlos.
    return UserProfile.model_validate(current_user)