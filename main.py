import asyncio
import os
import shutil

from PyInquirer import prompt
from src.config import TEMP_DOWNLOAD_PATH
from src.downloader import Downloader
from src.game_cfg import get_configs
from src.logging import logger


def remake_temp_dir() -> None:
    """Пересоздание временной папки для скачивания модов."""
    clean_temp_dir()
    if not os.path.exists(TEMP_DOWNLOAD_PATH):
        os.mkdir(TEMP_DOWNLOAD_PATH)


def clean_temp_dir() -> None:
    """Удаление временной папки для скачивания модов."""
    if os.path.exists(TEMP_DOWNLOAD_PATH):
        shutil.rmtree(TEMP_DOWNLOAD_PATH)


def download_mods() -> None:
    remake_temp_dir()
    configs = get_configs()

    selected_configs = []
    questions = [
        {
            "type": "checkbox",
            "name": "selected_configs",
            "message": "Выберите конфиги:",
            "choices": [{"name": config.name} for config in configs],
        }
    ]
    answers = prompt(questions)
    selected_configs = list(
        filter(lambda cfg: cfg.name in answers["selected_configs"], configs)
    )

    downloaders = [Downloader(cfg) for cfg in selected_configs]
    if len(downloaders) == 0:
        logger.info(
            "Никакой конфигурации выбрано не было. Завершение программы"
        )
        return

    loop = asyncio.get_event_loop()
    pool = [downloader.run() for downloader in downloaders]
    loop.run_until_complete(asyncio.wait(pool))
    loop.close()

    clean_temp_dir()
    logger.info("Завершено!")


def main() -> None:
    download_mods()


if __name__ == "__main__":
    main()
