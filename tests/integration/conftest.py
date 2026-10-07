from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registra los modelos en Base.metadata)
from app.core.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app


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


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    # Import local: mientras get_db no exista, fallan solo los tests que piden
    # este fixture y no toda la suite de integración.
    from app.db.session import get_db

    def override_get_db() -> Iterator[Session]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.clear()