from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

configure_logging()
app = FastAPI()
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.get("/health")
async def health_check():
    return {"status": "ok"}