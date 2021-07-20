import asyncio
import json
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from zipfile import ZipFile

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from rich.table import Table

from .cache import ModCache, dump_cache, load_cache
from .config import (
    CACHE_DIR,
    CHECK_STATUS_INTERVAL,
    CHUNK_DOWNLOAD_TIMEOUT,
    DOWNLOAD_CHUNK_SIZE,
    FILE_DOWNLOAD_TOTAL_TIMEOUT,
    SIMULTANEOUS_DOWNLOAD_MAX_COUNT,
    TEMP_DOWNLOAD_PATH,
)
from .game_cfg import GameConfig
from .logging import console


@dataclass
class ModInfo:
    """Информация о моде.

    Хранит название, id и UUID запроса на скачивание, назначаемый позже.
    """

    name: str
    mod_id: int
    last_update_date: str
    # file_size: int = -1
    request_uuid: Optional[str] = None

    @property
    def filename(self) -> str:
        """Название папки, в которую будет распакован мод.

        Например, в случае мода 'Better Balanced Starts (BBS)',
        у которого id=1958135962, папка будет иметь значение
        `1958135962_better_balanced_starts_bbs`.

        Returns:
            Название папки.
        """
        parts = [str(self.mod_id), *self.name.split(" ")]
        joined_parts = "_".join(parts).lower()
        return "".join(re.findall("[a-zA-Z0-9_\-'.]+", joined_parts))

    def __hash__(self) -> int:
        """Хеширование по ID мода."""
        return self.mod_id


class Downloader:
    """Загрузчик модов конфигурации игры."""

    def __init__(self, config: GameConfig) -> None:
        """Создание загрузчика.

        Args:
            config: Конфигурация игры.
        """
        self._config = config
        self._last_mod_update_cache: Dict[str, str] = {}
        if not os.path.exists(CACHE_DIR):
            os.mkdir(CACHE_DIR)
        self._cache = load_cache(self._cache_file_path)

    @lru_cache(1)
    def _list_mods_in_cfg_download_path(self) -> Set[str]:
        # Проверка на наличие папки и создание в случае её отсутствия
        if not os.path.exists(self._config.download_path):
            console.print(
                "Папка [cyan]%s[/cyan] отсутствует. Она будет создана"
                % self._config.download_path,
                style="warning",
            )
            os.mkdir(self._config.download_path)
        # Список установленных модов в этой папке
        mods = filter(
            lambda path: os.path.isdir(
                os.path.join(self._config.download_path, path)
            ),
            os.listdir(self._config.download_path),
        )
        return set(mods)

    @property
    def _cache_file_path(self) -> str:
        return str(CACHE_DIR / self._config.name) + ".json"

    def _dump_mod_to_cache(self, mod: ModInfo) -> None:
        self._cache[mod.mod_id] = {"last_update_date": mod.last_update_date}

    def _mod_has_to_be_redownloaded(self, mod: ModInfo) -> Tuple[bool, str]:
        # Проверка на то, что мод находится в установочном пути
        if mod.filename not in self._list_mods_in_cfg_download_path():
            return (True, "Не был установлен ранее")

        # Проверка на наличие кешированных данных о моде
        cached_mod_data: Optional[ModCache] = self._cache.get(mod.mod_id, None)
        if self._cache.get(mod.mod_id, None) is None:
            return (True, "В кеше не найдены данные")

        # Проверка на соответствие даты последнего обновления мода
        cached_last_update_date: str = cached_mod_data["last_update_date"]
        mod_is_outdated = cached_last_update_date != mod.last_update_date
        if mod_is_outdated:
            return (True, "Вышло новое обновление")

        return (False, "Нет обновлений")

    async def run(self) -> None:
        """Запуск загрузчика."""
        console.print("Получение информации о модах", style="info")
        mod_infos: List[ModInfo] = await asyncio.gather(
            *[self._get_mod_info(mod_id) for mod_id in self._config.mods]
        )

        mods_and_download_reasons: List[Tuple[bool, str]] = [
            self._mod_has_to_be_redownloaded(mod) for mod in mod_infos
        ]
        mod_infos_for_downloading: List[ModInfo] = []
        table = Table()
        table.add_column("ID")
        table.add_column("Мод")
        table.add_column("Описание")

        for mod, reason in sorted(
            zip(mod_infos, mods_and_download_reasons),
            key=lambda item: item[0].name,
        ):
            if reason[0]:
                mod_infos_for_downloading.append(mod)
            table.add_row(
                str(mod.mod_id),
                mod.name,
                reason[1],
                style=("warning" if reason[0] else "info"),
            )
        console.print(table)
        if len(mod_infos_for_downloading) == 0:
            console.print("Все моды установлены последней версии", style="info")
            return

        self._extract_mods(await self._download_mods(mod_infos_for_downloading))
        dump_cache(self._cache, self._cache_file_path)

    async def _download_mods(self, mods: List[ModInfo]) -> List[ModInfo]:
        sem = asyncio.Semaphore(SIMULTANEOUS_DOWNLOAD_MAX_COUNT)
        downloaded_mods: List[Optional[ModInfo]] = await asyncio.gather(
            *[self._process_mod(mod, sem) for mod in mods]
        )
        return list(filter(lambda x: x is not None, downloaded_mods))

    async def _get_mod_info(self, item_id: int) -> ModInfo:
        """Получение информации о моде по его ID, а конкретно - его название.

        Args:
            item_id: ID мода.

        Raises:
            ValueError: Ошибка получения информации о моде.

        Returns:
            Информация о моде.
        """
        info_url = f"http://steamworkshop.download/download/view/{item_id}"

        async with aiohttp.ClientSession() as session:
            response = await session.get(info_url)
        response.raise_for_status()

        soup = BeautifulSoup(await response.text(), "html.parser")

        error_elem = soup.find("div", "basic_errors")
        if error_elem:
            raise ValueError(error_elem.text)

        links = soup.find_all("a")
        try:
            title_elem = next(filter(lambda elem: "title" in elem.attrs, links))
        except StopIteration:
            raise ValueError("Не удалость получить название")

        item_name: str = title_elem.attrs["title"]

        last_update_elem = soup.find("div", "short-story")
        try:
            last_update_match = re.search("Update:.*", last_update_elem.text)
            last_update = last_update_match[0][8:]  # type: ignore
        except IndexError:
            raise ValueError(
                "Не удалость получить дату последнего обновления мода"
            )

        return ModInfo(item_name, item_id, last_update)

    # async def _process_mod_archive_sizes(
    #     self, out_mod_infos: Iterable[ModInfo]
    # ) -> None:
    #     url = "http://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v0001/"
    #     data = {
    #         "itemcount": len(out_mod_infos),
    #         "format": "json",
    #     }
    #     for index, mod in enumerate(out_mod_infos):
    #         data[f"publishedfileids[{index}]"] = mod.mod_id

    #     async with aiohttp.ClientSession() as session:
    #         response = await session.post(url, data=data)
    #     response_json = await response.json()

    #     for index, mod in enumerate(out_mod_infos):
    #         mod.file_size = int(
    #             response_json["response"]["publishedfiledetails"][index][
    #                 "file_size"
    #             ]
    #         )

    # Нельзя быстро получить много названий с оф сайта, не используя API
    # async def _get_mod_info(self, item_id: int) -> ModInfo:

    #     info_url = (
    #         f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"
    #     )

    #     async with aiohttp.ClientSession() as session:
    #         response = await session.get(info_url)
    #     response.raise_for_status()

    #     soup = BeautifulSoup(await response.text(), "html.parser")
    #     item_name: str = soup.find("div", "workshopItemTitle").text

    #     return ModInfo(item_name, item_id)

    ############################################################################
    # ---------- https://backend-03-prd.steamworkshopdownloader.io ----------- #
    ############################################################################
    async def _process_mod(
        self, mod: ModInfo, sem: asyncio.Semaphore
    ) -> Optional[ModInfo]:
        # POST Request:
        # https://backend-03-prd.steamworkshopdownloader.io/api/download/request
        # {
        #   "publishedFileId": 2266952591,
        #   "collectionId": null,
        #   "extract": true,
        #   "hidden": false,
        #   "direct": false,
        #   "autodownload": false
        # }
        #
        # Response:
        # {"uuid": "995afa62-18fe-4d94-9147-eb1d28b74f39"}
        async with sem:
            try:
                await self.make_request(mod)
            except Exception as err:
                console.print(
                    "Произошла ошибка при создании запроса на скачивание [cyan]%s[/cyan]. %s"
                    % (mod.name, err),
                    style="error",
                )
                return None

            completed = False
            while not completed:
                await asyncio.sleep(CHECK_STATUS_INTERVAL)
                try:
                    completed = await self._is_download_request_completed(mod)
                except Exception as err:
                    console.print(
                        "Произошла ошибка при проверке статуса запроса на скачивание [cyan]%s[/cyan]. %s"
                        % (mod.name, err),
                        style="error",
                    )
                    return None
            if not completed:
                return None

            try:
                await self._stream_download(mod)
            except Exception as err:
                console.print(
                    "Произошла ошибка при скачивании [cyan]%s[/cyan]. %s"
                    % (mod.name, err),
                    style="error",
                )
                return None
        self._dump_mod_to_cache(mod)
        return mod

    async def make_request(self, mod: ModInfo) -> None:
        request_url = "https://backend-03-prd.steamworkshopdownloader.io/api/download/request"
        data = {
            "publishedFileId": mod.mod_id,
            "collectionId": None,
            "extract": False,
            "hidden": False,
            "direct": False,
            "autodownload": False,
        }
        data_dumped = json.dumps(data)
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(data_dumped)),
        }
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    request_url, data=data_dumped, headers=headers
                )
            response.raise_for_status()
            text = await response.text()
            mod.request_uuid = json.loads(text)["uuid"]
        except Exception as err:
            console.print(
                "Произошла ошибка при получении UUID запроса на скачивание [cyan]%s[/cyan]. %s"
                % (mod.name, err),
                style="error",
            )

    async def _is_download_request_completed(self, mod: ModInfo) -> bool:
        """Проверить статус запроса на скачивание мода на сервере.

        Args:
            mod: Мод с указанным полем `request_uuid`.

        Returns:
            Готов к скачиванию или нет.
        """
        # POST Request:
        # https://backend-03-prd.steamworkshopdownloader.io/api/download/status
        # {"uuids":["995afa62-18fe-4d94-9147-eb1d28b74f39"]}
        #
        # Response:
        # {
        #   "995afa62-18fe-4d94-9147-eb1d28b74f39": {
        #     "age":14,
        #     "status": "prepared",
        #     "progress": 200,
        #     "progressText": "processed!",
        #     "downloadError": "never transmitted"
        #   }
        # }
        # console.print("Проверка статуса запросов на скачивание", style="debug")
        request_url = "https://backend-03-prd.steamworkshopdownloader.io/api/download/status"
        data = json.dumps({"uuids": [mod.request_uuid]})
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(data)),
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                request_url, data=data, headers=headers
            )

        text = await response.text()
        response_uuids = json.loads(text)
        for uuid, uuid_data in response_uuids.items():
            if uuid_data["status"] == "prepared":
                if uuid == mod.request_uuid:
                    return True
                console.print(
                    "Закончено скачивание на сервере [cyan]%s" % mod.name,
                    style="debug",
                )
        return False

    async def _stream_download(self, mod: ModInfo) -> ModInfo:
        # GET Request:
        # https://backend-03-prd.steamworkshopdownloader.io/api/download/transmit?uuid=995afa62-18fe-4d94-9147-eb1d28b74f39
        #
        # Response:
        # Content of a zip-archive
        request_url = (
            "https://backend-03-prd.steamworkshopdownloader.io/api/download/transmit?uuid=%s"
            % mod.request_uuid
        )
        console.print("Скачивание [cyan]%s" % mod.name, style="debug")
        timeout = aiohttp.ClientTimeout(
            total=FILE_DOWNLOAD_TOTAL_TIMEOUT,
            sock_read=CHUNK_DOWNLOAD_TIMEOUT,
            sock_connect=None,
            connect=None,
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await session.get(request_url)

            download_path = self._get_mod_temporary_download_path(mod)
            async with aiofiles.open(download_path, "wb") as out_file:
                while not response.content.at_eof():
                    content = await response.content.read(DOWNLOAD_CHUNK_SIZE)
                    await out_file.write(content)

        console.print("Завершено скачивание [cyan]%s" % mod.name, style="debug")
        return mod

    async def _gen_download(self, response, out_file) -> int:
        while True:
            content = await response.content.read(DOWNLOAD_CHUNK_SIZE)
            await out_file.write(content)
            yield
            if response.content.at_eof():
                return

    def _extract_mods(self, downloaded_mods: List[ModInfo]) -> None:
        console.print(
            "Распаковка модов в [cyan]%s" % self._config.download_path,
            style="info",
        )
        for mod in downloaded_mods:
            console.print(
                "Распаковка [cyan]%s[/cyan] в [cyan]%s"
                % (mod.name, mod.filename),
                style="debug",
            )

            from_filepath = self._get_mod_temporary_download_path(mod)
            to_filepath = self._get_mod_to_extract_path(mod)
            with ZipFile(from_filepath, "r") as archive:
                archive.extractall(to_filepath)

    def _get_mod_temporary_download_path(self, mod: ModInfo) -> str:
        """Путь к архиву мода во временной папке."""
        return str(TEMP_DOWNLOAD_PATH / mod.filename) + ".zip"

    def _get_mod_to_extract_path(self, mod: ModInfo) -> str:

        return str(Path(self._config.download_path) / mod.filename)

    ############################################################################
    # -------------------- http://steamworkshop.download/ -------------------- #
    ############################################################################
    # async def _get_download_link(
    #     self, mod_info: ModInfo, out_dict: Dict[str, str], lock: asyncio.Lock
    # ) -> None:
    #     logger.debug("Получение ссылки на скачивание '%s'" % mod_info.mod_name)
    #     data = {"item": mod_info.mod_id, "app": mod_info.app_id}
    #     headers = {"content-type": "application/x-www-form-urlencoded"}
    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(
    #             "http://steamworkshop.download/online/steamonline.php",
    #             data=data,
    #             headers=headers,
    #         ) as resp:
    #             response = await resp.text()
    #     soup = BeautifulSoup(response, "html.parser")

    #     download_link_tag = soup.find("a")
    #     if not download_link_tag:
    #         logger.error("Мод '%s' не был скачан" % mod_info.mod_name)
    #         return

    #     url = download_link_tag.attrs["href"]
    #     async with lock:
    #         out_dict[mod_info.filename] = url

    # async def _download_and_extract(self, url: str, filename: str) -> None:
    #     logger.debug("Скачивание '%s'" % filename)
    #     mod_place_folder = Path(os.path.abspath(self._config.download_path))
    #     if not os.path.exists(".download"):
    #         os.mkdir(".download")
    #     filepath = ".".join(
    #         (str(Path(".download") / filename), url.rsplit(".")[-1])
    #     )

    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as resp:
    #             if resp.status == 200:
    #                 f = await aiofiles.open(filepath, mode="wb")
    #                 await f.write(await resp.read())
    #                 await f.close()

    #     with ZipFile(filepath, "r") as archive:
    #         archive.extractall(".temp")
    #         folder = archive.namelist()[0]

    #     shutil.move(Path(".temp") / folder, mod_place_folder / filename)
    #     logger.debug("Скачан мод '%s'" % filename)
