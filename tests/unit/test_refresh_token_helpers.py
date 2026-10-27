import re

from app.core.security import generate_refresh_token, hash_refresh_token


def test_generate_refresh_token_devuelve_un_token_distinto_cada_vez():
    tokens = {generate_refresh_token() for _ in range(50)}

    assert len(tokens) == 50


def test_generate_refresh_token_tiene_al_menos_43_caracteres_url_safe():
    token = generate_refresh_token()

    assert len(token) >= 43  # 32 bytes aleatorios en base64 url-safe
    assert re.fullmatch(r"[A-Za-z0-9_-]+", token)


def test_hash_refresh_token_coincide_con_el_vector_conocido_de_sha256():
    # SHA-256 de "abc": vector de prueba estándar, independiente de nuestro código
    assert (
        hash_refresh_token("abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_hash_refresh_token_es_hexadecimal_de_64_caracteres():
    resultado = hash_refresh_token(generate_refresh_token())

    assert re.fullmatch(r"[0-9a-f]{64}", resultado)


def test_hash_refresh_token_es_determinista_y_distingue_entradas():
    assert hash_refresh_token("uno") == hash_refresh_token("uno")
    assert hash_refresh_token("uno") != hash_refresh_token("dos")