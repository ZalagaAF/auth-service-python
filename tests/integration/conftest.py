from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registra los modelos en Base.metadata)
from app.core.config import get_settings
from app.db.base import Base


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    settings = get_settings()
    test_url = settings.database_url.set(database=f"{settings.postgres_db}_test")

    # Guarda de seguridad: nunca operar sobre una base que no sea de tests.
    if not test_url.database.endswith("_test"):
        raise RuntimeError(
            f"Los tests deben correr contra una base '_test', no contra "
            f"'{test_url.database}'."
        )

    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()