from app.repositories.user_repository import UserRepository


def test_create_con_roles_los_asigna_al_usuario(db_session, base_roles):
    repo = UserRepository(db_session)

    usuario = repo.create(
        username="ana",
        email="ana@example.com",
        hashed_password="hash-de-prueba",
        roles=[base_roles["user"]],
    )

    db_session.expire_all()  # fuerza a leer de la base, no de memoria
    assert [rol.name for rol in usuario.roles] == ["user"]


def test_create_sin_roles_deja_al_usuario_sin_roles(db_session, base_roles):
    repo = UserRepository(db_session)

    usuario = repo.create(
        username="ana",
        email="ana@example.com",
        hashed_password="hash-de-prueba",
    )

    db_session.expire_all()
    assert usuario.roles == []