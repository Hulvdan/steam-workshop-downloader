import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, TypedDict, Union

import yaml
from schema import And, Schema, SchemaError, Use

from .logging import logger
from .utils import get_mod_id_from_url


@dataclass(frozen=True, eq=True)
class GameConfig:
    download_path: str
    mods: Set[int]
    name: str


class GameConfigDict(TypedDict):
    download_path: str
    mods: List[int]
    name: str


config_validation_schema = Schema(
    {
        "download_path": And(str, len),
        "mods": [Use(get_mod_id_from_url)],
    },
)


def get_configs(dir_path: str = "configs") -> List[GameConfig]:
    """Загрузка конфигов из папки.

    Args:
        dir_path: Папка, в которой находятся конфиги. Расширение должно быть yml
            или yaml.

    Returns:
        Список загруженных конфигов.
    """
    logger.info("Чтение конфигов...")
    configs: List[GameConfig] = []
    path = Path(dir_path)
    for file_path in os.listdir(path):
        if os.path.isfile(path / file_path):
            file_splitted = os.path.splitext(path / file_path)
            if file_splitted[1] in {".yml", ".yaml"}:
                cfg_name = os.path.splitext(file_path)[0]
                if cfg_name == "example":
                    continue
                logger.info("Найден конфиг '%s'" % cfg_name)
                cfg = _get_config(path / file_path, cfg_name)
                if cfg is not None:
                    configs.append(cfg)
    return configs


def _get_config(
    filepath: Union[str, os.PathLike], cfg_name: str
) -> Optional[GameConfig]:
    """Подгрузка конфига из файла и валидация."""
    with open(filepath) as cfg_file:
        cfg_data: GameConfigDict = yaml.safe_load(cfg_file)

    try:
        cfg_data = config_validation_schema.validate(cfg_data)
    except SchemaError as err:
        logger.error("Конфиг '%s' неверный! %s" % (cfg_name, err))
        return None

    unique_mods: Set[int] = set()
    for mod in cfg_data["mods"]:
        if mod in unique_mods:
            logger.warning("Найден дубликат мода: %s" % mod)
            continue
        unique_mods.add(mod)

    return GameConfig(cfg_data["download_path"], unique_mods, cfg_name)
