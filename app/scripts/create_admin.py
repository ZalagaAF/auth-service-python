import argparse
import sys

from sqlalchemy.orm import Session

from app.core.exceptions import RoleNotFoundError, UserNotFoundError
from app.core.roles import ROLE_ADMIN
from app.db.session import get_db
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


def promote_to_admin(session: Session, email: str) -> bool:
    """Agrega el rol admin a un usuario ya registrado.

    Devuelve True si se lo agregó y False si el usuario ya era admin.
    Conserva los roles que ya tenía.
    """
    normalized_email = email.strip().lower()

    user = UserRepository(session).get_by_email(normalized_email)
    if user is None:
        raise UserNotFoundError(normalized_email)

    admin_role = RoleRepository(session).get_by_name(ROLE_ADMIN)
    if admin_role is None:
        raise RoleNotFoundError(ROLE_ADMIN)

    if any(role.name == ROLE_ADMIN for role in user.roles):
        return False

    user.roles.append(admin_role)
    session.commit()
    return True


def run(email: str, session: Session) -> int:
    """Ejecuta la promoción e informa el resultado. Devuelve el código de salida."""
    normalized_email = email.strip().lower()

    try:
        promoted = promote_to_admin(session, normalized_email)
    except UserNotFoundError:
        print(
            f"Error: no existe un usuario registrado con el email {normalized_email}.",
            file=sys.stderr,
        )
        return 1
    except RoleNotFoundError:
        print(
            f"Error: el rol '{ROLE_ADMIN}' no existe en la base de datos. "
            "Ejecutá las migraciones con 'alembic upgrade head'.",
            file=sys.stderr,
        )
        return 1

    if promoted:
        print(f"{normalized_email} ahora tiene el rol {ROLE_ADMIN}.")
    else:
        print(f"{normalized_email} ya tenía el rol {ROLE_ADMIN}. No se hicieron cambios.")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Promueve a un usuario ya registrado al rol admin."
    )
    parser.add_argument("email", help="Email del usuario a promover")
    args = parser.parse_args(argv)

    # get_db es el generador que usa la aplicación: así el comando apunta
    # a la misma base de datos, sin depender del nombre de la fábrica de sesiones.
    sessions = get_db()
    session = next(sessions)
    try:
        exit_code = run(args.email, session)
    finally:
        sessions.close()  # ejecuta el cierre de la sesión que hace get_db
    sys.exit(exit_code)


if __name__ == "__main__":
    main()