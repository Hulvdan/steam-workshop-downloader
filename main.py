import asyncio
import os
import shutil

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


if __name__ == "__main__":
    remake_temp_dir()
    configs = get_configs()
    downloaders = [Downloader(cfg) for cfg in configs]

    loop = asyncio.get_event_loop()
    pool = [downloader.run() for downloader in downloaders]
    loop.run_until_complete(asyncio.wait(pool))
    loop.close()

    clean_temp_dir()
    logger.info("Завершено!")
