from app.core.config import Settings


def test_database_url_se_arma_con_las_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5433")

    settings = Settings(_env_file=None)

    assert (
        settings.database_url.render_as_string(hide_password=False)
        == "postgresql+psycopg://testuser:testpass@localhost:5433/testdb"
    )