from src.utils import get_mod_id_from_url


def test_link():
    assert (
        get_mod_id_from_url(
            "https://steamcommunity.com/sharedfiles/filedetails/?id=2266952591"
        )
        == 2266952591
    )


def test_number_str():
    assert get_mod_id_from_url("2266952591") == 2266952591


def test_number():
    assert get_mod_id_from_url(2266952591) == 2266952591
