import subprocess
import sys
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.models.refresh_tokens import RefreshToken
from app.models.users import User

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
TABLA = RefreshToken.__table__


def _grupos_unicos(table):
    """Conjuntos de columnas con unicidad, sin importar si es constraint, índice o unique=True."""
    grupos = [
        frozenset(c.name for c in cons.columns)
        for cons in table.constraints
        if isinstance(cons, UniqueConstraint)
    ]
    grupos += [frozenset(c.name for c in idx.columns) for idx in table.indexes if idx.unique]
    grupos += [frozenset({c.name}) for c in table.columns if c.unique]
    return grupos


def _grupos_indexados(table):
    return [frozenset(c.name for c in idx.columns) for idx in table.indexes]


def test_refresh_token_usa_la_tabla_refresh_tokens():
    assert RefreshToken.__tablename__ == "refresh_tokens"


def test_refresh_tokens_tiene_exactamente_estas_columnas():
    assert {c.name for c in TABLA.columns} == {
        "id",
        "user_id",
        "token_hash",
        "expires_at",
        "created_at",
        "revoked_at",
    }


def test_id_es_la_clave_primaria():
    assert [c.name for c in TABLA.primary_key.columns] == ["id"]


def test_id_y_user_id_tienen_el_mismo_tipo_que_users_id():
    tipo_users_id = type(User.__table__.c.id.type)
    assert type(TABLA.c.id.type) is tipo_users_id
    assert type(TABLA.c.user_id.type) is tipo_users_id


def test_user_id_no_admite_nulos():
    assert TABLA.c.user_id.nullable is False


def test_user_id_referencia_users_con_cascade():
    fks = {
        (fk.parent.name, fk.column.table.name, fk.column.name, fk.ondelete)
        for fk in TABLA.foreign_keys
    }
    assert fks == {("user_id", "users", "id", "CASCADE")}


def test_user_id_tiene_un_indice():
    assert frozenset({"user_id"}) in _grupos_indexados(TABLA)


def test_token_hash_no_admite_nulos():
    assert TABLA.c.token_hash.nullable is False


def test_token_hash_tiene_longitud_64():
    # SHA-256 en hexadecimal ocupa exactamente 64 caracteres
    assert TABLA.c.token_hash.type.length == 64


def test_token_hash_es_unico():
    assert frozenset({"token_hash"}) in _grupos_unicos(TABLA)


def test_expires_at_no_admite_nulos():
    assert TABLA.c.expires_at.nullable is False


def test_las_fechas_guardan_zona_horaria():
    for nombre in ("expires_at", "created_at", "revoked_at"):
        assert TABLA.c[nombre].type.timezone is True, nombre


def test_created_at_no_admite_nulos_y_tiene_valor_por_defecto_del_servidor():
    assert TABLA.c.created_at.nullable is False
    assert TABLA.c.created_at.server_default is not None


def test_revoked_at_admite_nulos():
    assert TABLA.c.revoked_at.nullable is True


def test_importar_app_models_registra_la_tabla():
    # Proceso nuevo: comprueba que app/models/__init__.py importa el modelo nuevo
    # (lo que necesitan Alembic y create_all), no solo lo que importó este archivo.
    codigo = (
        "import app.models; "
        "from app.db.base import Base; "
        "print(','.join(sorted(Base.metadata.tables)))"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ_PROYECTO,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    tablas = set(resultado.stdout.strip().split(","))
    assert "refresh_tokens" in tablas