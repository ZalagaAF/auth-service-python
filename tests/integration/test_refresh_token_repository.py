from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.refresh_tokens import RefreshToken
from app.models.users import User
from app.repositories.refresh_token_repository import RefreshTokenRepository


def _crear_usuario(db_session, sufijo="a"):
    usuario = User(
        username=f"usuario_{sufijo}",
        email=f"{sufijo}@example.com",
        hashed_password="hash-de-prueba",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _en_el_futuro():
    return datetime.now(timezone.utc) + timedelta(days=7)


def _contar(db_session, *condiciones):
    return db_session.scalar(
        select(func.count()).select_from(RefreshToken).where(*condiciones)
    )


def test_create_guarda_el_token_y_lo_devuelve(db_session):
    usuario = _crear_usuario(db_session)
    vence = _en_el_futuro()

    token = RefreshTokenRepository(db_session).create(
        user_id=usuario.id, token_hash="a" * 64, expires_at=vence
    )

    assert token.id is not None
    assert token.user_id == usuario.id
    assert token.token_hash == "a" * 64
    assert token.expires_at == vence
    assert token.revoked_at is None


def test_get_by_hash_devuelve_el_token_pedido(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())
    segundo = repo.create(
        user_id=usuario.id, token_hash="b" * 64, expires_at=_en_el_futuro()
    )
    segundo_id = segundo.id

    encontrado = repo.get_by_hash("b" * 64)

    assert encontrado is not None
    assert encontrado.id == segundo_id


def test_get_by_hash_devuelve_none_si_no_existe(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    # Hay un token guardado, así el None no se debe a una tabla vacía
    repo.create(user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro())

    assert repo.get_by_hash("z" * 64) is None


def test_rotate_revoca_el_token_viejo_y_crea_uno_nuevo_activo(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    viejo = repo.create(
        user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro()
    )
    momento = datetime.now(timezone.utc)

    nuevo = repo.rotate(viejo, "b" * 64, _en_el_futuro())

    assert nuevo is not None
    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    viejo_db = db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == "a" * 64)
    )
    nuevo_db = db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == "b" * 64)
    )
    assert abs(viejo_db.revoked_at - momento) < timedelta(seconds=5)
    assert nuevo_db is not None
    assert nuevo_db.revoked_at is None
    assert nuevo_db.user_id == usuario.id


def test_rotate_sobre_un_token_ya_revocado_devuelve_none_y_no_crea_nada(db_session):
    usuario = _crear_usuario(db_session)
    repo = RefreshTokenRepository(db_session)
    viejo = repo.create(
        user_id=usuario.id, token_hash="a" * 64, expires_at=_en_el_futuro()
    )
    assert repo.rotate(viejo, "b" * 64, _en_el_futuro()) is not None  # control

    segundo_intento = repo.rotate(viejo, "c" * 64, _en_el_futuro())

    assert segundo_intento is None
    assert _contar(db_session) == 2  # el viejo y el primer reemplazo, nada más


def test_revoke_all_for_user_revoca_solo_los_activos_de_ese_usuario(db_session):
    ana = _crear_usuario(db_session, "ana")
    beto = _crear_usuario(db_session, "beto")
    repo = RefreshTokenRepository(db_session)
    repo.create(user_id=ana.id, token_hash="a" * 64, expires_at=_en_el_futuro())
    ya_revocado = repo.create(
        user_id=ana.id, token_hash="b" * 64, expires_at=_en_el_futuro()
    )
    repo.rotate(ya_revocado, "c" * 64, _en_el_futuro())  # b queda revocado, c activo
    repo.create(user_id=beto.id, token_hash="d" * 64, expires_at=_en_el_futuro())
    db_session.expire_all()
    revocado_antes = db_session.scalar(
        select(RefreshToken.revoked_at).where(RefreshToken.token_hash == "b" * 64)
    )

    cantidad = repo.revoke_all_for_user(ana.id)

    assert cantidad == 2  # los activos de Ana: "a" y "c" (el "b" ya estaba revocado)
    db_session.expire_all()
    assert _contar(db_session, RefreshToken.user_id == ana.id, RefreshToken.revoked_at.is_(None)) == 0
    assert _contar(db_session, RefreshToken.user_id == beto.id, RefreshToken.revoked_at.is_(None)) == 1
    revocado_despues = db_session.scalar(
        select(RefreshToken.revoked_at).where(RefreshToken.token_hash == "b" * 64)
    )
    assert revocado_despues == revocado_antes  # no se pisó la fecha original


def test_revoke_all_for_user_sin_tokens_devuelve_cero(db_session):
    usuario = _crear_usuario(db_session)

    assert RefreshTokenRepository(db_session).revoke_all_for_user(usuario.id) == 0