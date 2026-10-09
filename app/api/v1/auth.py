from fastapi import APIRouter, status

from app.schemas.user import UserCreate, UserRead

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate):
    raise NotImplementedError