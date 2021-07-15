import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
from zipfile import ZipFile

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

from .game_cfg import GameConfig
from .logging import logger
from .utils import get_mod_id_from_url


@dataclass
class ModInfo:
    name: str
    mod_id: int
    request_uuid: Optional[str] = None

    @property
    def filename(self):
        return (
            "_".join([str(self.mod_id), *self.name.split(" ")])
            .lower()
            .replace("(", "")
            .replace(")", "")
        )

    def __hash__(self):
        return self.mod_id


DOWNLOAD_CHUNK_SIZE = 1024 * 16
TEMP_DOWNLOAD_PATH = Path(".temp")
CHECK_STATUS_INTERVAL = 0.5  # seconds


class Downloader:
    count = 0

    def __init__(self, config: GameConfig) -> None:
        self._config = config
        if __class__.count == 0:
            self._clean_temp_dir()
        __class__.count += 1
        if not os.path.exists(TEMP_DOWNLOAD_PATH):
            os.mkdir(TEMP_DOWNLOAD_PATH)

    def __del__(self):
        __class__.count -= 1
        if __class__.count == 0:
            self._clean_temp_dir()

    def _clean_temp_dir(self):
        if os.path.exists(TEMP_DOWNLOAD_PATH):
            shutil.rmtree(TEMP_DOWNLOAD_PATH)

    @property
    def mod_ids(self) -> List[int]:
        return [get_mod_id_from_url(mod) for mod in self._config.mods]

    async def run(self) -> None:
        logger.info("%s: Получение id'шников модов..." % self._config.name)
        mod_infos_pool = [self._get_mod_info(mod_id) for mod_id in self.mod_ids]
        logger.info("%s: Получение названий модов..." % self._config.name)
        mod_infos = await asyncio.gather(*mod_infos_pool)

        lock = asyncio.Lock()
        mod_infos_with_uuids: Set[ModInfo] = set()
        mod_request_pool = [
            self._make_request(mod_info, mod_infos_with_uuids, lock)
            for mod_info in mod_infos
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

    async def _get_mod_info(self, item_id: int) -> ModInfo:
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
            title_elem = next(filter(lambda x: "title" in x.attrs, links))
        except StopIteration:
            raise ValueError("Не удалость получить название")

        item_name: str = title_elem.attrs["title"]

        return ModInfo(item_name, item_id)

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
        # {"uuid":"995afa62-18fe-4d94-9147-eb1d28b74f39"}
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
            text = await response.text()
            mod_info.request_uuid = json.loads(text)["uuid"]
            async with lock:
                out_mods.add(mod_info)
        except Exception as err:
            logger.error(
                "Произошла ошибка при получении UUID запроса на скачивание '%s'. %s"
                % (mod_info.name, err)
            )

    async def _check_status(
        self, mod_infos_with_uuids: Set[ModInfo]
    ) -> Set[ModInfo]:
        """Проверить статус файлов.

        Args:
            uuids: Набор незавершённых UUID'ов.

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
        logger.info("Проверка статуса файлов...")
        request_url = "https://backend-03-prd.steamworkshopdownloader.io/api/download/status"
        data = {"uuids": list(mod.request_uuid for mod in mod_infos_with_uuids)}
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
                        lambda x: x.request_uuid == uuid, mod_infos_with_uuids
                    )
                )
                completed_mods.add(completed_mod)
                logger.debug(
                    "Закончено скачивание на сервере '%s'" % completed_mod.name
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
        logger.info("Скачивание '%s'..." % mod.name)
        async with aiohttp.ClientSession() as session:
            response = await session.get(request_url)

            download_path = self.get_mod_from_download_path(mod)
            async with aiofiles.open(download_path, "wb") as out_file:
                while not response.content.at_eof():
                    content = await response.content.read(DOWNLOAD_CHUNK_SIZE)
                    await out_file.write(content)

        logger.info("Завершено скачивание '%s'" % mod.name)
        return mod

    def _extract_mods(self, downloaded_mods: Set[ModInfo]) -> None:
        logger.info("Распаковка модов в '%s'" % self._config.download_path)
        for mod in downloaded_mods:
            logger.debug("Распаковка '%s'" % mod.name)

            from_filepath = self.get_mod_from_download_path(mod)
            to_filepath = self.get_mod_to_extract_path(mod)
            # print(from_filepath, to_filepath)
            with ZipFile(from_filepath, "r") as archive:
                archive.extractall(to_filepath)

    def get_mod_from_download_path(self, mod: ModInfo) -> str:
        return str(TEMP_DOWNLOAD_PATH / mod.filename) + ".zip"

    def get_mod_to_extract_path(self, mod: ModInfo) -> str:
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
