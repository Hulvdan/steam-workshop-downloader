from typing import List

import requests
from bs4 import BeautifulSoup

from .logging import logger


def validate_mod_ids(mod_ids: List[int]) -> bool:
    """Проверка на существование модов по их id.

    Args:
        mod_ids: Список ID модов.

    Returns:
        True, если все моды существуют. False в случае, если хотя бы один не
        найден.
    """
    all_valid = True
    for mod_id in mod_ids:
        if not _validate_mod_id(mod_id):
            logger.error("Не существует мода с id: '%s'" % mod_id)
            all_valid = False
    return all_valid


def _validate_mod_id(mod_id: int) -> bool:
    """Проверка на то, что мод с данным id существует.

    Производится GET запрос на сайт steamcommunity.com (не API), после чего
    идёт поиск элемента `div` с классом `error_ctn` - это карта, на которой
    отображается ошибка.

    Args:
        mod_id: ID мода.

    Returns:
        True, если мод существует. False в противном случае.
    """
    response = requests.get(
        "https://steamcommunity.com/sharedfiles/filedetails/?id=%s" % mod_id
    )
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find("div", "error_ctn") is None
