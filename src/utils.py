import re
from typing import Union
from urllib import parse


def get_mod_id_from_url(mod_url: Union[str, int]) -> int:
    if isinstance(mod_url, int):
        return mod_url
    assert isinstance(mod_url, str)
    if mod_url.isdecimal():
        return int(mod_url)
    parsed_url = parse.urlparse(mod_url)
    qs = parse.parse_qs(parsed_url.query)
    return int(qs["id"][0])
