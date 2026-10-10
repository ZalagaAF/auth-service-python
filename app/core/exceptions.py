class UserAlreadyExistsError(Exception):
    """Se intentó registrar un usuario cuyo email o username ya existen."""

class InvalidCredentialsError(Exception):
    """Las credenciales son inválidas o la cuenta no puede iniciar sesión."""