from app.core.security import hash_password, verify_password

PASSWORD = "Clave-segura-123"


def test_hash_password_no_devuelve_la_contrasena_en_texto_plano():
    hashed = hash_password(PASSWORD)

    assert isinstance(hashed, str)
    assert hashed != PASSWORD
    assert PASSWORD not in hashed


def test_hash_password_usa_argon2id():
    assert hash_password(PASSWORD).startswith("$argon2id$")


def test_la_misma_contrasena_produce_hashes_distintos():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_password_acepta_la_contrasena_correcta():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_verify_password_rechaza_una_contrasena_incorrecta():
    assert verify_password("otra-clave-123", hash_password(PASSWORD)) is False


def test_verify_password_distingue_mayusculas():
    assert verify_password(PASSWORD.lower(), hash_password(PASSWORD)) is False


def test_verify_password_funciona_con_caracteres_unicode():
    password = "contraseña-ñandú-🔑"

    assert verify_password(password, hash_password(password)) is True


def test_verify_password_no_trunca_contrasenas_largas():
    larga = "a" * 200
    hashed = hash_password(larga)

    assert verify_password(larga, hashed) is True
    assert verify_password(larga + "b", hashed) is False