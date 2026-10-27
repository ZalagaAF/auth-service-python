from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_auth_service, get_current_user
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
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


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        user = service.authenticate(email=credentials.email, password=credentials.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = service.issue_refresh_token(user)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        user, new_refresh_token = service.refresh(body.refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)

@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user