import json
import os
from typing import Dict, TypedDict, Union

from schema import And, Schema, SchemaError

from .logging import logger


class ModCache(TypedDict):
    """Кешированные данные о моде."""

    last_update_date: str


cache_schema = Schema({"last_update_date": And(str, len)})


def load_cache(path: Union[str, os.PathLike]) -> Dict[int, ModCache]:
    """Загрузка кеша из файла.

    Args:
        path: Путь к файлу, из которого будет загружен кеш.

    Returns:
        Кеш.
    """
    if not os.path.exists(path):
        logger.info("Кеш отсутствует. Все моды будут заново скачаны")
        return {}
    logger.info("Загрузка кеша '%s'" % path)
    with open(path) as cache_file:
        cache = json.load(cache_file)
    try:
        return cache_schema.validate(cache)
    except SchemaError as err:
        logger.warning(
            "Кеш не валиден. Все моды будут заново скачаны. %s " % err
        )
        return {}


def dump_cache(
    cache: Dict[int, ModCache], path: Union[str, os.PathLike]
) -> None:
    """Запись кеша в файл.

    Args:
        cache: Кеш.
        path: Путь к файлу, куда будет записан кеш.
    """
    logger.info("Кеширование '%s'" % path)
    with open(path, "w") as cache_file:
        json.dump(cache, cache_file)
