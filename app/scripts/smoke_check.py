"""Prueba de humo contra la API en ejecución.

Recorre: salud, registro, login, perfil, acceso prohibido, refresh y logout.
Uso:  python scripts/smoke_check.py [URL_BASE]    (por defecto http://127.0.0.1:8000)
Crea un usuario nuevo en cada corrida. Solo usa la librería estándar.
"""

import json
import sys
import urllib.error
import urllib.request
import uuid

PASSWORD = "Clave-segura-123"


def pedir(metodo, url, cuerpo=None, token=None):
    """Hace un pedido HTTP y devuelve (estado, json_o_None)."""
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    pedido = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=10) as respuesta:
            contenido = respuesta.read()
            estado = respuesta.status
    except urllib.error.HTTPError as error:
        contenido = error.read()
        estado = error.code
    try:
        return estado, (json.loads(contenido) if contenido else None)
    except json.JSONDecodeError:
        return estado, None


def esperar(paso, estado, esperado):
    if estado != esperado:
        print(f"FALLO  {paso}: se esperaba {esperado} y llegó {estado}")
        sys.exit(1)
    print(f"OK     {paso}")


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    api = f"{base}/api/v1"
    sufijo = uuid.uuid4().hex[:8]
    usuario = f"smoke_{sufijo}"
    email = f"smoke-{sufijo}@example.com"

    try:
        estado, cuerpo = pedir("GET", f"{base}/health")
    except urllib.error.URLError as error:
        print(f"FALLO  no se pudo conectar con {base}: {error.reason}")
        sys.exit(1)
    esperar("GET /health", estado, 200)
    assert cuerpo == {"status": "ok"}, cuerpo

    estado, cuerpo = pedir(
        "POST",
        f"{api}/auth/register",
        {"username": usuario, "email": email, "password": PASSWORD},
    )
    esperar("registro", estado, 201)
    user_id = cuerpo["id"]

    estado, cuerpo = pedir(
        "POST", f"{api}/auth/login", {"email": email, "password": PASSWORD}
    )
    esperar("login", estado, 200)
    access, refresh = cuerpo["access_token"], cuerpo["refresh_token"]

    estado, cuerpo = pedir("GET", f"{api}/users/me", token=access)
    esperar("perfil", estado, 200)
    assert cuerpo["id"] == user_id and cuerpo["roles"] == ["user"], cuerpo

    estado, _ = pedir("GET", f"{api}/users", token=access)
    esperar("listado de usuarios sin ser admin (debe dar 403)", estado, 403)

    estado, cuerpo = pedir("POST", f"{api}/auth/refresh", {"refresh_token": refresh})
    esperar("refresh", estado, 200)
    assert cuerpo["refresh_token"] != refresh, "el refresh token no rotó"
    access, refresh = cuerpo["access_token"], cuerpo["refresh_token"]

    estado, _ = pedir("GET", f"{api}/users/me", token=access)
    esperar("perfil con el access token renovado", estado, 200)

    estado, _ = pedir("POST", f"{api}/auth/logout", {"refresh_token": refresh})
    esperar("logout", estado, 204)

    estado, _ = pedir("POST", f"{api}/auth/refresh", {"refresh_token": refresh})
    esperar("refresh después del logout (debe dar 401)", estado, 401)

    estado, _ = pedir(
        "POST", f"{api}/auth/login", {"email": email, "password": "otra-clave-123"}
    )
    esperar("login con contraseña incorrecta (debe dar 401)", estado, 401)

    print("Todo OK: el servicio responde como se espera.")


if __name__ == "__main__":
    main()