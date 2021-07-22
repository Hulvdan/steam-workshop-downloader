import json
import os
from functools import lru_cache
from tempfile import TemporaryFile
from typing import Any, Dict, Union
from zipfile import ZipFile

import requests
from src.config import VERSION
from src.logging import console


def handle_update() -> None:
    """Обновление программы до последней версии."""
    console.print("Получение ссылки на скачивание...", style="debug")
    data = _get_latest_release_data()
    download_url = _get_release_download_link(data)

    with TemporaryFile() as archive:
        console.print("Скачивание...", style="debug")
        _download_release_archive(download_url, archive)

        console.print("Распакова...", style="debug")
        _extract_release_archive(archive, os.curdir)


def is_running_latest_version() -> bool:
    """Проверка на то, установлена ли последняя версия программы."""
    data = _get_latest_release_data()
    latest_release_version = _get_release_tag(data)
    return latest_release_version == VERSION


@lru_cache(1)
def _get_latest_release_data() -> Dict[str, Any]:
    """Получение данных о последнем релизе программы с GitHub."""
    url = "https://api.github.com/repos/Hulvdan/steam-workshop-downloader/releases/latest"  # noqa: E501
    response = requests.get(url)
    response.raise_for_status()
    return json.loads(response.text)


def _get_release_tag(release_data: Dict[str, Any]) -> str:
    """Получение тега релиза программы."""
    return release_data["tag_name"]


def _get_release_download_link(release_data: Dict[str, Any]) -> str:
    """Получение ссылки на скачивание архива программы."""
    return release_data["assets"][0]["browser_download_url"]


def _download_release_archive(url: str, to_file: TemporaryFile) -> None:
    """Скачивание архива."""
    response = requests.get(url)
    to_file.write(response.content)


def _extract_release_archive(
    archive_file: TemporaryFile, extract_path: Union[str, os.PathLike]
) -> None:
    """Распаковка архива программы."""
    with ZipFile(archive_file, "r") as archive:
        archive.extractall(extract_path)
