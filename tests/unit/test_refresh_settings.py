from app.core.config import get_settings


def test_refresh_token_expire_days_tiene_un_default_de_7_dias():
    assert get_settings().refresh_token_expire_days == 7