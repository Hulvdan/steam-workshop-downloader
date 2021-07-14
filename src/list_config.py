import json
import os
from dataclasses import dataclass
from typing import Dict, List

from schema import And, Schema
from pathlib import Path


@dataclass
class Config:
    download_path: str
    mods: List[str]


config_validation_schema = Schema(
    And(
        {
            "download_path": And(str, len),
            "mods": And(list),
        },
    )
)


def get_configs(path: str = "config") -> Dict[str, Config]:
    configs: Dict[str, Config] = {}
    path = Path(path)
    for file_path in os.listdir(path):
        if os.path.isfile(path / file_path):
            file_splitted = os.path.splitext(path / file_path)
            if file_splitted[1] == ".json":
                cfg_name = os.path.splitext(file_path)[0]
                if cfg_name == 'example':
                    continue
                cfg = _get_config(path / file_path)
                configs[cfg_name] = cfg
    return configs


def _get_config(filepath: str) -> Config:
    with open(filepath) as cfg_file:
        cfg_data = json.load(cfg_file)
        config_validation_schema.validate(cfg_data)
    cfg = Config(cfg_data["download_path"], cfg_data["mods"])
    return cfg
