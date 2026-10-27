from datetime import datetime, timedelta, timezone

from sqlalchemy import select

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


def _revocado_en(db_session, token_hash):
    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    return db_session.scalar(
        select(RefreshToken.revoked_at).where(RefreshToken.token_hash == token_hash)
    )


def test_revoke_by_hash_revoca_solo_ese_token_y_devuelve_true(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())
    repo.create(user_id=usuario.id, token_hash="b" * 64, expires_at=_en_el_futuro())
    momento = datetime.now(timezone.utc)

    resultado = repo.revoke_by_hash("a" * 64)

    assert resultado is True
    assert abs(_revocado_en(db_session, "a" * 64) - momento) < timedelta(seconds=5)
    assert _revocado_en(db_session, "b" * 64) is None


def test_revoke_by_hash_sobre_un_token_ya_revocado_devuelve_false_y_no_pisa_la_fecha(
    db_session,
):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())
    assert repo.revoke_by_hash("a" * 64) is True  # control: la primera vez revoca
    fecha_original = _revocado_en(db_session, "a" * 64)

    resultado = repo.revoke_by_hash("a" * 64)

    assert resultado is False
    assert _revocado_en(db_session, "a" * 64) == fecha_original


def test_revoke_by_hash_con_un_hash_desconocido_devuelve_false(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())

    resultado = repo.revoke_by_hash("z" * 64)

    assert resultado is False
    assert _revocado_en(db_session, "a" * 64) is None