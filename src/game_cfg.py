import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import yaml
from schema import And, Schema, SchemaError

from .logging import logger


@dataclass
class GameConfig:
    download_path: str
    mods: List[str]
    name: str


config_validation_schema = Schema(
    And(
        {
            "download_path": And(str, len),
            "mods": And(list),
        },
    )
)


def get_configs(directory_path: str = "config") -> List[GameConfig]:
    logger.info("Чтение конфигов...")
    configs: List[GameConfig] = []
    path = Path(directory_path)
    for file_path in os.listdir(path):
        if os.path.isfile(path / file_path):
            file_splitted = os.path.splitext(path / file_path)
            if file_splitted[1] in {".yml", ".yaml"}:
                cfg_name = os.path.splitext(file_path)[0]
                if cfg_name == "example":
                    continue
                logger.info("Найден конфиг '%s'" % cfg_name)
                cfg = _get_config(path / file_path, cfg_name)
                if cfg:
                    configs.append(cfg)
    return configs


def _get_config(
    filepath: Union[str, os.PathLike], cfg_name: str
) -> Optional[GameConfig]:
    with open(filepath) as cfg_file:
        cfg_data = yaml.load(cfg_file)

    try:
        config_validation_schema.validate(cfg_data)
    except SchemaError as err:
        logger.error("Конфиг '%s' неверный! %s" % (cfg_name, err))
        return None

    return GameConfig(cfg_data["download_path"], cfg_data["mods"], cfg_name)
