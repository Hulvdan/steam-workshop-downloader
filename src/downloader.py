import asyncio
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set
from zipfile import ZipFile

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from .cache import ModCache, dump_cache, load_cache
from .config import (
    CACHE_DIR,
    CHECK_STATUS_INTERVAL,
    DOWNLOAD_CHUNK_SIZE,
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
        return "".join(re.findall("[a-zA-Z0-9_]+", joined_parts))

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

    def _mod_has_to_be_redownloaded(self, mod: ModInfo) -> bool:
        # Проверка на то, что мод находится в установочном пути
        if mod.filename not in self._list_mods_in_cfg_download_path():
            self._cache[mod.mod_id] = {"last_update_date": mod.last_update_date}
            console.print(
                "Мод '%s' не был найден в пути установки." % mod.name,
                style="warning",
            )
            return True

        # Проверка на наличие кешированных данных о моде
        cached_mod_data: Optional[ModCache] = self._cache.get(mod.mod_id, None)
        if self._cache.get(mod.mod_id, None) is None:
            self._cache[mod.mod_id] = {"last_update_date": mod.last_update_date}
            console.print(
                "В кеше не найдены данные мода '%s'" % mod.name, style="warning"
            )
            return True

        # Проверка на соответствие даты последнего обновления мода
        cached_last_update_date: str = cached_mod_data["last_update_date"]
        mod_is_outdated = cached_last_update_date != mod.last_update_date
        if mod_is_outdated:
            console.print(
                "Вышло новое обновление мода '%s'" % mod.name, style="info"
            )
            self._cache[mod.mod_id] = {"last_update_date": mod.last_update_date}
            return True

        console.print(
            "Мод '%s' установлен последней версии" % mod.name, style="info"
        )
        return False

    async def run(self) -> None:
        """Запуск загрузчика."""
        console.print(
            "%s: Получение названий модов..." % self._config.name,
            style="info",
        )
        mod_infos: List[ModInfo] = await asyncio.gather(
            *[self._get_mod_info(mod_id) for mod_id in self._config.mods]
        )

        mod_infos_for_downloading: List[ModInfo] = list(
            filter(lambda mod: self._mod_has_to_be_redownloaded(mod), mod_infos)
        )
        if len(mod_infos_for_downloading) == 0:
            return

        lock = asyncio.Lock()
        mod_infos_with_uuids: Set[ModInfo] = set()
        mod_request_pool = [
            self._make_request(mod_info, mod_infos_with_uuids, lock)
            for mod_info in mod_infos_for_downloading
        ]
        await asyncio.wait(mod_request_pool)

        await asyncio.sleep(2)
        completed_mods: Set[ModInfo] = set()
        while len(mod_infos_with_uuids) > 0:
            completed_mods |= await self._check_status(mod_infos_with_uuids)
            mod_infos_with_uuids -= completed_mods
            await asyncio.sleep(CHECK_STATUS_INTERVAL)

        downloaded_mods = await asyncio.gather(
            *[self._stream_download(mod) for mod in completed_mods]
        )

        self._extract_mods(downloaded_mods)
        dump_cache(self._cache, self._cache_file_path)

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
    async def _make_request(
        self,
        mod_info: ModInfo,
        out_mods: Set[ModInfo],
        lock: asyncio.Lock,
    ) -> None:
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
        request_url = "https://backend-03-prd.steamworkshopdownloader.io/api/download/request"
        data = {
            "publishedFileId": mod_info.mod_id,
            "collectionId": None,
            "extract": True,
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
            mod_info.request_uuid = json.loads(text)["uuid"]
            async with lock:
                out_mods.add(mod_info)
        except Exception as err:
            console.print(
                "Произошла ошибка при получении UUID запроса на скачивание '%s'. %s"
                % (mod_info.name, err),
                style="error",
            )

    async def _check_status(self, mods: Set[ModInfo]) -> Set[ModInfo]:
        """Проверить статус файлов.

        Args:
            mods: Набор информация о модах, в которых указаны поля
                  `request_uuid`.

        Returns:
            Набор завершённых UUID'ов.
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
        console.print("Проверка статуса файлов...", style="info")
        request_url = "https://backend-03-prd.steamworkshopdownloader.io/api/download/status"
        data = {"uuids": [mod.request_uuid for mod in mods]}
        data_dumped = json.dumps(data)
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(data_dumped)),
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                request_url, data=data_dumped, headers=headers
            )

        completed_mods: Set[ModInfo] = set()
        resp_text = await response.text()
        response_uuids = json.loads(resp_text)
        for uuid, uuid_data in response_uuids.items():
            if uuid_data["status"] == "prepared":
                completed_mod = next(
                    filter(
                        lambda mod: mod.request_uuid == uuid,
                        mods,
                    )
                )
                completed_mods.add(completed_mod)
                console.print(
                    "Закончено скачивание на сервере '%s'" % completed_mod.name,
                    style="info",
                )

        return completed_mods

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
        console.print("Скачивание '%s'..." % mod.name, style="info")
        async with aiohttp.ClientSession() as session:
            response = await session.get(request_url)

            download_path = self._get_mod_temporary_download_path(mod)
            async with aiofiles.open(download_path, "wb") as out_file:
                while not response.content.at_eof():
                    content = await response.content.read(DOWNLOAD_CHUNK_SIZE)
                    await out_file.write(content)

        console.print("Завершено скачивание '%s'" % mod.name, style="info")
        return mod

    def _extract_mods(self, downloaded_mods: List[ModInfo]) -> None:
        console.print(
            "Распаковка модов в '%s'" % self._config.download_path, style="info"
        )
        for mod in downloaded_mods:
            console.print("Распаковка '%s'" % mod.name, style="info")

            from_filepath = self._get_mod_temporary_download_path(mod)
            to_filepath = self._get_mod_to_extract_path(mod)
            # print(from_filepath, to_filepath)
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
