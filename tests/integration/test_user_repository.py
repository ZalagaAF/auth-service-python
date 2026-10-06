import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repository import UserRepository


@pytest.fixture
def user_repository(db_session):
    return UserRepository(db_session)


def test_crear_devuelve_el_usuario_con_sus_datos(user_repository):
    user = user_repository.create(
        username="ana", email="ana@example.com", hashed_password="hash"
    )

    assert user.username == "ana"
    assert user.email == "ana@example.com"
    assert user.hashed_password == "hash"


def test_crear_completa_los_valores_automaticos(user_repository):
    user = user_repository.create(
        username="ana", email="ana@example.com", hashed_password="hash"
    )

    assert isinstance(user.id, uuid.UUID)
    assert user.is_active is True
    assert user.created_at is not None


def test_get_by_email_encuentra_a_un_usuario_existente(user_repository):
    creado = user_repository.create(
        username="ana", email="ana@example.com", hashed_password="hash"
    )

    encontrado = user_repository.get_by_email("ana@example.com")

    assert encontrado is not None
    assert encontrado.id == creado.id


def test_get_by_email_devuelve_none_si_no_existe(user_repository):
    assert user_repository.get_by_email("nadie@example.com") is None


def test_crear_con_email_duplicado_falla(user_repository):
    user_repository.create(
        username="ana", email="ana@example.com", hashed_password="hash"
    )

    with pytest.raises(IntegrityError):
        user_repository.create(
            username="otra", email="ana@example.com", hashed_password="hash"
        )


def test_crear_con_username_duplicado_falla(user_repository):
    user_repository.create(
        username="ana", email="ana@example.com", hashed_password="hash"
    )

    with pytest.raises(IntegrityError):
        user_repository.create(
            username="ana", email="otra@example.com", hashed_password="hash"
        )


def test_la_sesion_sigue_usable_despues_de_un_duplicado(user_repository):
    user_repository.create(
        username="ana", email="ana@example.com", hashed_password="hash"
    )

    with pytest.raises(IntegrityError):
        user_repository.create(
            username="otra", email="ana@example.com", hashed_password="hash"
        )

    existente = user_repository.get_by_email("ana@example.com")

    assert existente is not None
    assert existente.username == "ana"