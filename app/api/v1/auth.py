from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_auth_service
from app.core.exceptions import UserAlreadyExistsError
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        return service.register(
            username=user_in.username,
            email=user_in.email,
            password=user_in.password,
        )
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario o el email ya están registrados.",
        )