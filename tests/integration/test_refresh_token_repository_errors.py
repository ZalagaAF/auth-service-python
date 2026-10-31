from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.refresh_tokens import RefreshToken
from app.models.users import User
from app.repositories.refresh_token_repository import RefreshTokenRepository


def _crear_usuario(db_session):
    usuario = User(
        username="usuario_a",
        email="a@example.com",
        hashed_password="hash-de-prueba",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _en_el_futuro():
    return datetime.now(timezone.utc) + timedelta(days=7)


def test_create_con_un_hash_repetido_lanza_integrity_error_y_deja_la_sesion_usable(
    db_session,
):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())

    with pytest.raises(IntegrityError):
        repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())

    # Tras el rollback, la sesión sigue funcionando y el primero sigue guardado
    assert repo.get_by_hash("a" * 64) is not None


def test_si_falla_el_reemplazo_el_token_viejo_no_queda_revocado(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    viejo = repo.create(
        user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro()
    )
    repo.create(user_id=usuario.id, token_hash="b" * 64, expires_at=_en_el_futuro())

    with pytest.raises(IntegrityError):
        repo.rotate(viejo, "b" * 64, _en_el_futuro())  # el hash del reemplazo ya existe

    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    revocado_en = db_session.scalar(
        select(RefreshToken.revoked_at).where(RefreshToken.token_hash == "a" * 64)
    )
    assert revocado_en is None  # la revocación se deshizo junto con el intento fallido