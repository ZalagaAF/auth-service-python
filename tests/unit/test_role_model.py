import subprocess
import sys
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.models.roles import Role
from app.models.user_roles import user_roles
from app.models.users import User

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


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


def test_role_usa_la_tabla_roles():
    assert Role.__tablename__ == "roles"


def test_roles_tiene_solo_id_y_name():
    assert {c.name for c in Role.__table__.columns} == {"id", "name"}


def test_roles_id_es_la_clave_primaria():
    assert [c.name for c in Role.__table__.primary_key.columns] == ["id"]


def test_roles_id_tiene_el_mismo_tipo_que_users_id():
    assert type(Role.__table__.c.id.type) is type(User.__table__.c.id.type)


def test_roles_name_no_admite_nulos():
    assert Role.__table__.c.name.nullable is False


def test_roles_name_es_unico():
    assert frozenset({"name"}) in _grupos_unicos(Role.__table__)


def test_roles_name_tiene_longitud_maxima_50():
    assert Role.__table__.c.name.type.length == 50


def test_user_roles_tiene_solo_user_id_y_role_id():
    assert user_roles.name == "user_roles"
    assert {c.name for c in user_roles.columns} == {"user_id", "role_id"}


def test_user_roles_tiene_clave_primaria_compuesta():
    assert {c.name for c in user_roles.primary_key.columns} == {"user_id", "role_id"}


def test_user_roles_tiene_claves_foraneas_con_cascade():
    fks = {
        fk.parent.name: (fk.column.table.name, fk.column.name, fk.ondelete)
        for fk in user_roles.foreign_keys
    }
    assert fks == {
        "user_id": ("users", "id", "CASCADE"),
        "role_id": ("roles", "id", "CASCADE"),
    }


def test_importar_app_models_registra_todas_las_tablas():
    # Proceso nuevo: así comprobamos que app/models/__init__.py importa todo
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
    assert {"users", "roles", "user_roles"} <= tablas