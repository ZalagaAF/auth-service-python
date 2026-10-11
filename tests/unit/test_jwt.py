import time
from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError
from app.core.security import create_access_token, decode_access_token

SECRET = "clave-de-prueba-" + "x" * 32
ALGORITHM = "HS256"
EXPIRE_MINUTES = 15


@pytest.fixture(autouse=True)
def configuracion_de_prueba(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", ALGORITHM)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(EXPIRE_MINUTES))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_access_token_devuelve_un_jwt_de_tres_partes():
    token = create_access_token(subject="user-123")

    assert isinstance(token, str)
    assert len(token.split(".")) == 3


def test_el_token_contiene_el_subject():
    token = create_access_token(subject="user-123")

    assert decode_access_token(token)["sub"] == "user-123"


def test_el_token_expira_segun_la_configuracion():
    claims = decode_access_token(create_access_token(subject="user-123"))

    assert claims["exp"] - claims["iat"] == EXPIRE_MINUTES * 60


def test_se_puede_indicar_una_duracion_propia():
    token = create_access_token(subject="user-123", expires_delta=timedelta(minutes=1))

    claims = decode_access_token(token)

    assert claims["exp"] - claims["iat"] == 60


def test_un_token_vencido_es_rechazado():
    token = create_access_token(
        subject="user-123", expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_un_token_alterado_es_rechazado():
    original = create_access_token(subject="user-123")
    ajeno = create_access_token(subject="admin")
    header, _, firma = original.split(".")
    _, payload_ajeno, _ = ajeno.split(".")

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{payload_ajeno}.{firma}")


def test_un_token_firmado_con_otra_clave_es_rechazado():
    ahora = int(time.time())
    token = jwt.encode(
        {"sub": "user-123", "iat": ahora, "exp": ahora + 600},
        "otra-clave-distinta-" + "y" * 32,
        algorithm=ALGORITHM,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_un_token_sin_firma_con_alg_none_es_rechazado():
    ahora = int(time.time())
    token = jwt.encode(
        {"sub": "user-123", "iat": ahora, "exp": ahora + 600},
        key=None,
        algorithm="none",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_un_token_sin_vencimiento_es_rechazado():
    token = jwt.encode({"sub": "user-123"}, SECRET, algorithm=ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_un_token_sin_subject_es_rechazado():
    ahora = int(time.time())
    token = jwt.encode({"iat": ahora, "exp": ahora + 600}, SECRET, algorithm=ALGORITHM)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("token", ["", "no-es-un-token", "a.b.c"])
def test_un_texto_que_no_es_un_token_es_rechazado(token):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)