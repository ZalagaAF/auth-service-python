from slowapi import Limiter
from slowapi.util import get_remote_address

LOGIN_MAX_ATTEMPTS = 5
LOGIN_RATE_LIMIT = "5/minute"
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
limiter = Limiter(key_func=get_remote_address)