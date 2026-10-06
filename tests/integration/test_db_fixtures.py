from sqlalchemy import text

from app.models import User


def test_la_conexion_a_la_base_responde(db_session):
    resultado = db_session.execute(text("SELECT 1")).scalar()

    assert resultado == 1


def test_los_tests_corren_contra_la_base_de_tests(db_session):
    nombre_base = db_session.execute(text("SELECT current_database()")).scalar()

    assert nombre_base.endswith("_test")


def test_la_tabla_users_existe_y_esta_vacia(db_session):
    cantidad = db_session.execute(text("SELECT count(*) FROM users")).scalar()

    assert cantidad == 0


def test_a_un_usuario_insertado_es_visible_dentro_del_test(db_session):
    db_session.add(
        User(username="ana", email="ana@example.com", hashed_password="hash")
    )
    db_session.flush()

    cantidad = db_session.execute(text("SELECT count(*) FROM users")).scalar()

    assert cantidad == 1


def test_b_el_usuario_del_test_anterior_ya_no_existe(db_session):
    cantidad = db_session.execute(text("SELECT count(*) FROM users")).scalar()

    assert cantidad == 0