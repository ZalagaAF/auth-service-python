from app.repositories.user_repository import UserRepository

NOMBRES = ["carla", "ana", "eva", "beto", "dario"]  # a propósito, fuera de orden


def _crear_usuarios(db_session):
    repo = UserRepository(db_session)
    for nombre in NOMBRES:
        repo.create(
            username=nombre,
            email=f"{nombre}@example.com",
            hashed_password="hash-de-prueba",
        )
    return repo


def test_list_paginated_ordena_por_username(db_session):
    repo = _crear_usuarios(db_session)

    usuarios = repo.list_paginated(limit=10, offset=0)

    assert [u.username for u in usuarios] == ["ana", "beto", "carla", "dario", "eva"]


def test_list_paginated_aplica_limit_y_offset(db_session):
    repo = _crear_usuarios(db_session)

    pagina = repo.list_paginated(limit=2, offset=2)

    assert [u.username for u in pagina] == ["carla", "dario"]


def test_list_paginated_con_offset_mas_alla_del_total_devuelve_lista_vacia(db_session):
    repo = _crear_usuarios(db_session)

    assert repo.list_paginated(limit=10, offset=50) == []


def test_count_devuelve_el_total_de_usuarios(db_session):
    repo = UserRepository(db_session)
    assert repo.count() == 0  # control: tabla vacía

    _crear_usuarios(db_session)

    assert repo.count() == 5