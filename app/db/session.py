from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url)

# Se ejercita de verdad en scripts/smoke_check.py, que corre contra el contenedor:
# los tests lo reemplazan por la sesión de prueba.
def get_db() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session