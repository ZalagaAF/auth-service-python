import uuid

import pytest

from app.repositories.user_repository import UserRepository

URL = "/api/v1/auth/register"
PASSWORD = "Clave-segura-123"


def datos_validos(**cambios: str) -> dict[str, str]:
    datos = {"username": "ana", "email": "ana@example.com", "password": PASSWORD}
    return {**datos, **cambios}


def test_registro_correcto_devuelve_201_con_los_datos_publicos(client):
    response = client.post(URL, json=datos_validos())

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "ana"
    assert body["email"] == "ana@example.com"
    assert body["is_active"] is True
    assert "created_at" in body
    uuid.UUID(body["id"])  # lanza ValueError si no es un UUID válido


def test_la_respuesta_no_expone_la_contrasena(client):
    response = client.post(URL, json=datos_validos())

    assert response.status_code == 201
    body = response.json()
    assert "password" not in body
    assert "hashed_password" not in body


def test_la_contrasena_se_guarda_hasheada(client, db_session):
    client.post(URL, json=datos_validos())

    user = UserRepository(db_session).get_by_email("ana@example.com")

    assert user is not None
    assert PASSWORD not in user.hashed_password


def test_email_duplicado_devuelve_409(client):
    client.post(URL, json=datos_validos())

    response = client.post(URL, json=datos_validos(username="otra"))

    assert response.status_code == 409


def test_username_duplicado_devuelve_409(client):
    client.post(URL, json=datos_validos())

    response = client.post(URL, json=datos_validos(email="otra@example.com"))

    assert response.status_code == 409


@pytest.mark.parametrize("email", ["no-es-un-email", "ana@", "@example.com", ""])
def test_email_con_formato_invalido_devuelve_422(client, email):
    response = client.post(URL, json=datos_validos(email=email))

    assert response.status_code == 422


@pytest.mark.parametrize("password", ["", "1234567"])
def test_contrasena_de_menos_de_8_caracteres_devuelve_422(client, password):
    response = client.post(URL, json=datos_validos(password=password))

    assert response.status_code == 422


def test_contrasena_de_exactamente_8_caracteres_es_valida(client):
    response = client.post(URL, json=datos_validos(password="12345678"))

    assert response.status_code == 201


@pytest.mark.parametrize("campo", ["username", "email", "password"])
def test_faltando_un_campo_devuelve_422(client, campo):
    datos = datos_validos()
    del datos[campo]

    response = client.post(URL, json=datos)

    assert response.status_code == 422


def test_el_email_se_guarda_y_se_devuelve_en_minusculas(client, db_session):
    response = client.post(URL, json=datos_validos(email="ANA@Example.com"))

    assert response.status_code == 201
    assert response.json()["email"] == "ana@example.com"
    assert UserRepository(db_session).get_by_email("ana@example.com") is not None


def test_email_duplicado_con_otras_mayusculas_devuelve_409(client):
    client.post(URL, json=datos_validos())

    response = client.post(
        URL, json=datos_validos(username="otra", email="ANA@EXAMPLE.COM")
    )

    assert response.status_code == 409


def test_despues_de_un_duplicado_se_puede_registrar_a_otro_usuario(client):
    client.post(URL, json=datos_validos())
    duplicado = client.post(URL, json=datos_validos(username="otra"))
    assert duplicado.status_code == 409

    response = client.post(
        URL, json=datos_validos(username="beto", email="beto@example.com")
    )

    assert response.status_code == 201