import pytest

from app.repositories.user_repository import UserRepository

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"


@pytest.fixture
def usuario_registrado(client):
    response = client.post(
        REGISTER_URL,
        json={"username": "ana", "email": EMAIL, "password": PASSWORD},
    )
    assert response.status_code == 201


def login(client, **cambios):
    datos = {"email": EMAIL, "password": PASSWORD}
    return client.post(LOGIN_URL, json={**datos, **cambios})


def test_login_correcto_devuelve_200_con_un_token_bearer(client, usuario_registrado):
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"] != ""


def test_login_correcto_no_expone_datos_sensibles(client, usuario_registrado):
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert "password" not in body
    assert "hashed_password" not in body


def test_login_normaliza_el_email(client, usuario_registrado):
    response = login(client, email="ANA@Example.com")

    assert response.status_code == 200


def test_contrasena_incorrecta_devuelve_401_con_www_authenticate(
    client, usuario_registrado
):
    response = login(client, password="otra-clave-123")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_email_inexistente_devuelve_401(client, usuario_registrado):
    response = login(client, email="nadie@example.com")

    assert response.status_code == 401


def test_mismo_cuerpo_de_error_para_email_inexistente_y_contrasena_incorrecta(
    client, usuario_registrado
):
    inexistente = login(client, email="nadie@example.com")
    incorrecta = login(client, password="otra-clave-123")

    assert inexistente.status_code == 401
    assert incorrecta.status_code == 401
    assert inexistente.json() == incorrecta.json()


def test_usuario_inactivo_devuelve_401(client, usuario_registrado, db_session):
    user = UserRepository(db_session).get_by_email(EMAIL)
    user.is_active = False
    db_session.commit()

    response = login(client)

    assert response.status_code == 401


@pytest.mark.parametrize("campo", ["email", "password"])
def test_faltando_un_campo_devuelve_422(client, campo):
    datos = {"email": EMAIL, "password": PASSWORD}
    del datos[campo]

    response = client.post(LOGIN_URL, json=datos)

    assert response.status_code == 422


def test_email_con_formato_invalido_devuelve_422(client):
    response = login(client, email="no-es-un-email")

    assert response.status_code == 422