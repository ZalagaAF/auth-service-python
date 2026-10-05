from app.models.users import User

table = User.__table__
columns = table.columns


def test_la_tabla_se_llama_users():
    assert table.name == "users"


def test_la_tabla_tiene_exactamente_las_columnas_esperadas():
    assert set(columns.keys()) == {
        "id",
        "username",
        "email",
        "hashed_password",
        "is_active",
        "created_at",
    }


def test_id_es_clave_primaria():
    assert columns["id"].primary_key is True


def test_email_es_obligatorio_y_unico():
    assert columns["email"].nullable is False
    assert columns["email"].unique is True


def test_username_es_obligatorio_y_unico():
    assert columns["username"].nullable is False
    assert columns["username"].unique is True


def test_hashed_password_es_obligatorio_y_no_existe_columna_password():
    assert columns["hashed_password"].nullable is False
    assert "password" not in columns.keys()


def test_is_active_es_verdadero_por_defecto():
    assert columns["is_active"].default.arg is True


def test_created_at_es_obligatorio_y_tiene_default_en_la_base():
    assert columns["created_at"].nullable is False
    assert columns["created_at"].server_default is not None