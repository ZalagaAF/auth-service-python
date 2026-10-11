import pytest
from pydantic import ValidationError

from app.core.config import Settings

SECRET = "s" * 32


@pytest.fixture
def entorno(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    return monkeypatch


def test_database_url_se_arma_con_las_variables_de_entorno(entorno):
    settings = Settings(_env_file=None)

    assert (
        settings.database_url.render_as_string(hide_password=False)
        == "postgresql+psycopg://testuser:testpass@localhost:5433/testdb"
    )


def test_jwt_tiene_valores_por_defecto(entorno):
    entorno.delenv("JWT_ALGORITHM", raising=False)
    entorno.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

    settings = Settings(_env_file=None)

    assert settings.jwt_secret_key == SECRET
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 15


def test_jwt_se_configura_desde_el_entorno(entorno):
    entorno.setenv("JWT_ALGORITHM", "HS512")
    entorno.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")

    settings = Settings(_env_file=None)

    assert settings.jwt_algorithm == "HS512"
    assert settings.access_token_expire_minutes == 5


def test_la_clave_secreta_de_jwt_es_obligatoria(entorno):
    entorno.delenv("JWT_SECRET_KEY")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_la_clave_secreta_de_jwt_demasiado_corta_se_rechaza(entorno):
    entorno.setenv("JWT_SECRET_KEY", "corta")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_los_minutos_de_expiracion_deben_ser_positivos(entorno):
    entorno.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)