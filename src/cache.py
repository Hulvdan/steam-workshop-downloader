import json
import os
from typing import Dict, TypedDict, Union

from schema import And, Schema, SchemaError, Use

from .logging import console


class ModCache(TypedDict):
    """Кешированные данные о моде."""

    last_update_date: str


cache_schema = Schema({Use(int): {"last_update_date": And(str, len)}})


def load_cache(path: Union[str, os.PathLike]) -> Dict[int, ModCache]:
    """Загрузка кеша из файла.

    Args:
        path: Путь к файлу, из которого будет загружен кеш.

    Returns:
        Кеш.
    """
    if not os.path.exists(path):
        console.print(
            "Кеш отсутствует. Все моды будут заново скачаны", style="warning"
        )
        return {}
    console.print("Загрузка кеша [cyan]'%s'" % path, style="info")
    with open(path) as cache_file:
        cache = json.load(cache_file)
    try:
        return cache_schema.validate(cache)
    except SchemaError as err:
        console.print(
            "Кеш не валиден. Все моды будут заново скачаны. %s" % err,
            style="warning",
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
    console.print("Кеширование [cyan]'%s'" % path, style="info")
    with open(path, "w") as cache_file:
        json.dump(cache, cache_file, indent=4, sort_keys=True)
