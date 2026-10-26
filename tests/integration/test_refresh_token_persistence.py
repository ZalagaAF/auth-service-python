import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.models.refresh_tokens import RefreshToken
from app.models.users import User


def _crear_usuario(db_session, sufijo="a"):
    usuario = User(
        username=f"usuario_{sufijo}",
        email=f"{sufijo}@example.com",
        hashed_password="hash-de-prueba",
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario


def _nuevo_token(usuario_id, token_hash="a" * 64, **cambios):
    datos = {
        "user_id": usuario_id,
        "token_hash": token_hash,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return RefreshToken(**{**datos, **cambios})


def test_se_puede_guardar_y_leer_un_refresh_token(db_session):
    usuario = _crear_usuario(db_session)
    vence = datetime.now(timezone.utc) + timedelta(days=7)
    token = _nuevo_token(usuario.id, expires_at=vence)
    db_session.add(token)
    db_session.flush()
    token_id = token.id
    assert isinstance(token_id, uuid.UUID)

    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    leido = db_session.scalar(select(RefreshToken).where(RefreshToken.id == token_id))

    assert leido is not None
    assert leido.user_id == usuario.id
    assert leido.token_hash == "a" * 64
    assert leido.expires_at == vence
    assert leido.expires_at.tzinfo is not None
    assert leido.revoked_at is None
    assert leido.created_at is not None


def test_no_se_pueden_guardar_dos_tokens_con_el_mismo_hash(db_session):
    usuario = _crear_usuario(db_session)
    db_session.add(_nuevo_token(usuario.id))
    db_session.flush()

    db_session.add(_nuevo_token(usuario.id))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_no_se_puede_guardar_un_token_de_un_usuario_inexistente(db_session):
    db_session.add(_nuevo_token(uuid.uuid4()))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_un_usuario_puede_tener_varios_tokens(db_session):
    usuario = _crear_usuario(db_session)
    db_session.add_all(
        [_nuevo_token(usuario.id, "a" * 64), _nuevo_token(usuario.id, "b" * 64)]
    )
    db_session.flush()

    cantidad = db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.user_id == usuario.id)
    )
    assert cantidad == 2


def test_revocar_un_token_guarda_la_fecha_con_zona_horaria(db_session):
    usuario = _crear_usuario(db_session)
    token = _nuevo_token(usuario.id)
    db_session.add(token)
    db_session.flush()
    token_id = token.id

    momento = datetime.now(timezone.utc)
    token.revoked_at = momento
    db_session.flush()
    db_session.expire_all()

    leido = db_session.scalar(select(RefreshToken).where(RefreshToken.id == token_id))
    assert leido.revoked_at == momento
    assert leido.revoked_at.tzinfo is not None


def test_borrar_un_usuario_borra_sus_refresh_tokens(db_session):
    usuario = _crear_usuario(db_session)
    db_session.add(_nuevo_token(usuario.id))
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(RefreshToken)) == 1

    # DELETE de Core (sin cascadas del ORM): tiene que ser la base quien aplique ON DELETE CASCADE
    db_session.execute(delete(User).where(User.id == usuario.id))

    assert db_session.scalar(select(func.count()).select_from(RefreshToken)) == 0