from fastapi import FastAPI

from app.api.v1.auth import router as auth_router

from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter, rate_limit_exceeded_handler

from app.core.logging_config import configure_logging

configure_logging()
app = FastAPI()
app.include_router(auth_router, prefix="/api/v1")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.get("/health")
async def health_check():
    return {"status": "ok"}