import asyncio
import os
import shutil

from PyInquirer import prompt
from src.config import TEMP_DOWNLOAD_PATH
from src.downloader import Downloader
from src.game_cfg import get_configs
from src.logging import console
from update import handle_update, is_running_latest_version


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
    configs = get_configs()

    selected_configs = []
    selectable_configs = [{"name": config.name} for config in configs]
    if len(selectable_configs) == 0:
        console.print(
            "Не найдено конфигураций. Создайте новую.\n"
            "Посмотрите [cyan]README.md[/cyan], чтобы узнать подробнее",
            style="warning",
        )
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
    if not answers:
        console.print("Завершение программы", style="warning")
        return

    selected_configs = list(
        filter(lambda cfg: cfg.name in answers["selected_configs"], configs)
    )

    remake_temp_dir()
    downloaders = [Downloader(cfg) for cfg in selected_configs]
    if len(downloaders) == 0:
        console.print(
            "Никакой конфигурации выбрано не было. Завершение программы",
            style="warning",
        )
        return

    asyncio.run(downloaders[0].run())

    clean_temp_dir()
    console.print("[cyan]Завершено!")


def main() -> None:
    console.print(
        "steam-workshop-downloader",
        style="black on yellow",
        justify="center",
    )
    console.print(
        "https://github.com/Hulvdan/steam-workshop-downloader",
        style="italic red on yellow",
        justify="center",
    )
    if is_running_latest_version():
        console.print("Установлена последняя версия!", style="info")
    else:
        questions = [
            {
                "type": "confirm",
                "name": "update",
                "message": "Обновиться до последней версии программы?",
                "default": True,
            }
        ]
        answer = prompt(questions)
        if answer and answer["update"]:
            handle_update()
            return

    download_mods()
    console.input("\nНажмите [cyan]Enter[/cyan], чтобы выйти.")


if __name__ == "__main__":
    main()
