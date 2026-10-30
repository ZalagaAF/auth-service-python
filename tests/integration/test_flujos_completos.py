import pytest

from app.repositories.user_repository import UserRepository
from app.scripts.create_admin import promote_to_admin

pytestmark = pytest.mark.usefixtures("base_roles")

API = "/api/v1"
PASSWORD = "Clave-segura-123"


def _esperar(respuesta, estado, paso):
    """Compara el código de estado e indica QUÉ paso del recorrido se rompió."""
    assert respuesta.status_code == estado, (
        f"{paso}: se esperaba {estado} y llegó {respuesta.status_code} -> {respuesta.text}"
    )
    return respuesta


class Usuario:
    """Una persona recorriendo la API: guarda sus tokens y arma los pedidos."""

    def __init__(self, client, username):
        self.client = client
        self.username = username
        self.email = f"{username}@example.com"
        self.id = None
        self.access_token = None
        self.refresh_token = None

    def registrarse(self):
        respuesta = _esperar(
            self.client.post(
                f"{API}/auth/register",
                json={
                    "username": self.username,
                    "email": self.email,
                    "password": PASSWORD,
                },
            ),
            201,
            f"registro de {self.username}",
        )
        self.id = respuesta.json()["id"]

    def iniciar_sesion(self):
        respuesta = _esperar(
            self.client.post(
                f"{API}/auth/login",
                json={"email": self.email, "password": PASSWORD},
            ),
            200,
            f"login de {self.username}",
        )
        self.access_token = respuesta.json()["access_token"]
        self.refresh_token = respuesta.json()["refresh_token"]

    def get(self, ruta):
        return self.client.get(
            f"{API}{ruta}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

    def renovar(self, refresh_token=None):
        """Pide un par nuevo y devuelve la respuesta tal cual, sin guardar nada."""
        return self.client.post(
            f"{API}/auth/refresh",
            json={"refresh_token": refresh_token or self.refresh_token},
        )

    def renovar_y_guardar(self):
        respuesta = _esperar(self.renovar(), 200, f"renovación de {self.username}")
        self.access_token = respuesta.json()["access_token"]
        self.refresh_token = respuesta.json()["refresh_token"]

    def cerrar_sesion(self):
        _esperar(
            self.client.post(
                f"{API}/auth/logout", json={"refresh_token": self.refresh_token}
            ),
            204,
            f"logout de {self.username}",
        )


def test_recorrido_de_un_usuario_comun_desde_el_registro_hasta_el_logout(client):
    ana = Usuario(client, "ana")
    ana.registrarse()
    ana.iniciar_sesion()

    # Acceso protegido: puede ver su perfil, pero no el listado de admins
    perfil = _esperar(ana.get("/users/me"), 200, "perfil")
    assert perfil.json()["id"] == ana.id
    assert perfil.json()["roles"] == ["user"]
    _esperar(ana.get("/users"), 403, "listado de usuarios sin ser admin")

    # Renovación: el par nuevo funciona
    refresh_viejo = ana.refresh_token
    ana.renovar_y_guardar()
    assert ana.refresh_token != refresh_viejo
    _esperar(ana.get("/users/me"), 200, "perfil con el access token renovado")

    # Reutilizar el refresh token viejo es un intento de robo
    _esperar(
        ana.renovar(refresh_viejo), 401, "reutilización del refresh token viejo"
    )
    # ...y cierra todas las sesiones: ni el refresh token nuevo sirve ya
    _esperar(ana.renovar(), 401, "renovar con el token nuevo tras la reutilización")

    # Se puede volver a empezar con una sesión limpia
    ana.iniciar_sesion()
    _esperar(ana.get("/users/me"), 200, "perfil tras volver a iniciar sesión")

    # Logout: el refresh token deja de servir
    ana.cerrar_sesion()
    _esperar(ana.renovar(), 401, "renovar después del logout")


def test_un_usuario_promovido_a_admin_usa_el_listado_con_el_mismo_token(
    client, db_session
):
    ana = Usuario(client, "ana")
    ana.registrarse()
    ana.iniciar_sesion()
    beto = Usuario(client, "beto")
    beto.registrarse()
    _esperar(ana.get("/users"), 403, "listado antes de ser admin")  # control

    assert promote_to_admin(db_session, ana.email) is True

    listado = _esperar(
        ana.get("/users"), 200, "listado tras la promoción, con el mismo token"
    )
    assert [u["username"] for u in listado.json()["items"]] == ["ana", "beto"]
    perfil = _esperar(ana.get("/users/me"), 200, "perfil de la admin")
    assert perfil.json()["roles"] == ["admin", "user"]

    # La renovación conserva los permisos
    ana.renovar_y_guardar()
    _esperar(ana.get("/users"), 200, "listado con el access token renovado")


def test_un_usuario_desactivado_pierde_el_acceso_por_todas_las_puertas(
    client, db_session
):
    ana = Usuario(client, "ana")
    ana.registrarse()
    ana.iniciar_sesion()
    _esperar(ana.get("/users/me"), 200, "perfil antes de desactivarla")  # control

    usuario = UserRepository(db_session).get_by_email(ana.email)
    usuario.is_active = False
    db_session.commit()

    _esperar(ana.get("/users/me"), 401, "perfil con un access token ya emitido")
    _esperar(ana.renovar(), 401, "renovación con un refresh token ya emitido")
    login = client.post(
        f"{API}/auth/login", json={"email": ana.email, "password": PASSWORD}
    )
    _esperar(login, 401, "login de una cuenta desactivada")


def test_cada_usuario_ve_solo_su_perfil_y_sus_sesiones_son_independientes(client):
    ana = Usuario(client, "ana")
    beto = Usuario(client, "beto")
    for usuario in (ana, beto):
        usuario.registrarse()
        usuario.iniciar_sesion()
    assert ana.id != beto.id

    perfil_de_ana = _esperar(ana.get("/users/me"), 200, "perfil de ana")
    perfil_de_beto = _esperar(beto.get("/users/me"), 200, "perfil de beto")
    assert perfil_de_ana.json()["id"] == ana.id
    assert perfil_de_beto.json()["id"] == beto.id

    # El logout de ana, y un intento de reutilizar su token, no tocan a beto
    ana.cerrar_sesion()
    _esperar(ana.renovar(), 401, "renovación de ana tras su logout")
    beto.renovar_y_guardar()
    _esperar(beto.get("/users/me"), 200, "perfil de beto después de todo lo de ana")