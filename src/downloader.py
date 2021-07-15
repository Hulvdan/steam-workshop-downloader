import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
from urllib import parse
from zipfile import ZipFile

import aiohttp

from .list_config import Config
from .logging import logger


@dataclass
class ModInfo:
    mod_name: str
    mod_id: int
    app_name: str
    app_id: int

    @property
    def filename(self):
        return (
            "_".join([str(self.mod_id), *self.mod_name.split(" ")])
            .lower()
            .replace("(", "")
            .replace(")", "")
        )


class Downloader:
    count = 0

    def __init__(self, config: Config) -> None:
        self._config = config
        if __class__.count == 0:
            self._clean_temp_dirs()

        __class__.count += 1

    def __del__(self):
        __class__.count -= 1
        if __class__.count == 0:
            self._clean_temp_dirs()

    def _clean_temp_dirs(self):
        if os.path.exists(".download"):
            shutil.rmtree(".download")
        if os.path.exists(".temp"):
            shutil.rmtree(".temp")

    def _get_mod_id_from_url(self, mod_url: str) -> int:
        parsed_url = parse.urlparse(mod_url)
        qs = parse.parse_qs(parsed_url.query)
        return int(qs["id"][0])

    async def run(self) -> None:
        logger.info("%s: Получение id'шников модов..." % self._config.name)
        mod_ids = [self._get_mod_id_from_url(mod) for mod in self._config.mods]
        mod_request_pool = [self._make_request(mod_id) for mod_id in mod_ids]

        mod_request_uuids = set(await asyncio.gather(*mod_request_pool))
        completed_uuids = set()
        while len(mod_request_uuids) > 0:
            completed_uuids |= await self._check_status(mod_request_uuids)
            mod_request_uuids -= completed_uuids
            await asyncio.sleep(0.3)

        await asyncio.wait(
            [self._stream_download(uuid) for uuid in completed_uuids]
        )

    ############################################################################
    # ---------- https://backend-03-prd.steamworkshopdownloader.io ----------- #
    ############################################################################
    async def _make_request(self, mod_id: int) -> str:
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
            "publishedFileId": 2266952591,
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
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                request_url, data=data_dumped, headers=headers
            )
        text = await response.text()
        return json.loads(text)["uuid"]

    async def _check_status(self, uuids: Set[str]) -> Set[str]:
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
        data = {"uuids": list(uuids)}
        data_dumped = json.dumps(data)
        headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(data_dumped)),
        }
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                request_url, data=data_dumped, headers=headers
            )

        completed_uuids: Set[str] = set()
        resp_text = await response.text()
        response_uuids = json.loads(resp_text)
        for uuid, uuid_data in response_uuids.items():
            if uuid_data["status"] == "prepared":
                completed_uuids.add(uuid)
                logger.debug(
                    "Закончено скачивание файла на сервере '%s'" % uuid
                )

        return completed_uuids

    async def _stream_download(self, uuid: str) -> None:
        # GET Request:
        # https://backend-03-prd.steamworkshopdownloader.io/api/download/transmit?uuid=995afa62-18fe-4d94-9147-eb1d28b74f39
        #
        # Response:
        # Content as a zip-file
        request_url = (
            "https://backend-03-prd.steamworkshopdownloader.io/api/download/transmit?uuid=%s"
            % uuid
        )
        logger.info("Получение ответа %s" % uuid)
        async with aiohttp.ClientSession() as session:
            response = await session.get(request_url)

            logger.info("Запись файла %s" % uuid)
            with open("test.zip", "wb") as out_file:
                while not response.content.at_eof():
                    logger.info("Запись кусочка...")
                    out_file.write(await response.content.read(8192))
            response.close()

        logger.info("Записано %s" % uuid)

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

    # async def _get_mod_info(self, item_id: int) -> ModInfo:
    #     info_url = f"http://steamworkshop.download/download/view/{item_id}"

    #     async with aiohttp.ClientSession() as session:
    #         response = await session.get(info_url)
    #     response.raise_for_status()

    #     soup = BeautifulSoup(await response.text(), "html.parser")

    #     error_elem = soup.find("div", "basic_errors")
    #     if error_elem:
    #         raise ValueError(error_elem.text)

    #     links = soup.find_all("a")
    #     try:
    #         title_elem = next(filter(lambda x: "title" in x.attrs, links))
    #     except StopIteration:
    #         raise ValueError("Не удалость получить название")

    #     item_name: str = title_elem.attrs["title"]
    #     app_name: str = title_elem.next_element.next_element[2:-1]

    #     try:
    #         expr = r"({item: [0-9]*, app: [0-9]*})"
    #         data = re.search(expr, await response.text())[0]  # type: ignore
    #         app_id: int = int(re.findall(r"[0-9]+", data)[1])  # type: ignore
    #     except IndexError:
    #         raise ValueError("Не удалось получить ID игры")

    #     return ModInfo(item_name, item_id, app_name, app_id)

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
