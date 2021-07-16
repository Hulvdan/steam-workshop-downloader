from src.cache import load_cache


def test_load_cache():
    assert load_cache("tests/cache.json") == {
        2266952591: {"last_update_date": "24.04.2021 / 08:50"}
    }
