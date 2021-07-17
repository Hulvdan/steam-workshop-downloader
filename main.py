import asyncio
import os
import shutil

from PyInquirer import prompt
from src.config import TEMP_DOWNLOAD_PATH
from src.downloader import Downloader
from src.game_cfg import get_configs
from src.logging import console


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
    console.print(
        "steam-workshop-downloader", style="black on yellow", justify="center"
    )
    remake_temp_dir()
    configs = get_configs()

    selected_configs = []
    selectable_configs = [{"name": config.name} for config in configs]
    if len(selectable_configs) == 0:
        console.print("Не найдено конфигураций. Создайте новую")
        return

    questions = [
        {
            "type": "list",
            "name": "selected_configs",
            "message": "Выберите конфиг:",
            "choices": selectable_configs,
        }
    ]
    answers = prompt(questions)
    selected_configs = list(
        filter(lambda cfg: cfg.name in answers["selected_configs"], configs)
    )

    downloaders = [Downloader(cfg) for cfg in selected_configs]
    if len(downloaders) == 0:
        console.print(
            "Никакой конфигурации выбрано не было. Завершение программы",
            style="warning",
        )
        return

    loop = asyncio.get_event_loop()
    pool = [downloader.run() for downloader in downloaders]
    loop.run_until_complete(asyncio.wait(pool))
    loop.close()

    clean_temp_dir()
    console.print("[cyan]Завершено!")


def main() -> None:
    download_mods()
    console.input("Нажмите [cyan]Enter[/cyan], чтобы выйти.")


if __name__ == "__main__":
    main()
