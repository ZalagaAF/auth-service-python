"""UserRepository.get_by_id: búsqueda de usuarios por id, contra Postgres real."""

import uuid

from app.repositories.user_repository import UserRepository


def test_get_by_id_devuelve_el_usuario(db_session):
    repo = UserRepository(db_session)
    creado = repo.create(
        username="ana", email="ana@example.com", hashed_password="hash-de-prueba"
    )
    creado_id = creado.id
    db_session.expire_all()  # fuerza a leer de la base, no de memoria

    encontrado = repo.get_by_id(creado_id)

    assert encontrado is not None
    assert encontrado.id == creado_id
    assert encontrado.email == "ana@example.com"


def test_get_by_id_devuelve_el_usuario_correcto_entre_varios(db_session):
    repo = UserRepository(db_session)
    repo.create(username="ana", email="ana@example.com", hashed_password="hash-1")
    beto = repo.create(
        username="beto", email="beto@example.com", hashed_password="hash-2"
    )
    beto_id = beto.id

    encontrado = repo.get_by_id(beto_id)

    assert encontrado is not None
    assert encontrado.username == "beto"


def test_get_by_id_devuelve_none_si_no_existe(db_session):
    repo = UserRepository(db_session)
    # Hay un usuario guardado, así el None no se debe a una tabla vacía
    repo.create(username="ana", email="ana@example.com", hashed_password="hash-1")

    assert repo.get_by_id(uuid.uuid4()) is None