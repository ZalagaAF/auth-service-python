class UserAlreadyExistsError(Exception):
    """Se intentó registrar un usuario cuyo email o username ya existen."""

class InvalidCredentialsError(Exception):
    """Las credenciales son inválidas o la cuenta no puede iniciar sesión."""

class InvalidTokenError(Exception):
    """El Toker es invalido"""

class DefaultRoleNotFoundError(Exception):
    """El rol base no existe en la base de datos.

    Es un error de configuración del servidor (falta sembrar los roles),
    no un error del cliente: por eso no hereda de las excepciones que se
    traducen a respuestas 4xx.
    """

class InvalidRefreshTokenError(Exception):
    """El refresh token es desconocido, venció, fue reutilizado o su usuario está inactivo.

    Se traduce a un 401 uniforme. No hereda de las demás excepciones de dominio
    para que ningún handler existente la capture por herencia.
    """

class UserNotFoundError(Exception):
    """No existe un usuario registrado con ese email."""

class RoleNotFoundError(Exception):
    """El rol pedido no existe en la base de datos (¿faltan las migraciones?)."""