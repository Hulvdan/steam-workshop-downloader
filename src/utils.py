from typing import Any
from urllib import parse

from .logging import console


def get_mod_id_from_url(mod_url: Any) -> int:
    """Получение ID мода из конфига."""
    if isinstance(mod_url, int):
        return mod_url

    if not isinstance(mod_url, str):
        msg = "Это не строка: '%s'" % mod_url
        console.print(msg, style="error")
        raise ValueError(msg)

    if mod_url.isdecimal():
        return int(mod_url)

    parsed_url = parse.urlparse(mod_url)
    qs = parse.parse_qs(parsed_url.query)
    try:
        return int(qs["id"][0])
    except KeyError:
        msg = "Невозможно получить ID из '%s'" % mod_url
        console.print(msg, style="error")
        raise ValueError(msg)
