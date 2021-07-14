import asyncio
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from urllib import parse
from zipfile import ZipFile

import aiofiles
import aiohttp
import requests
from bs4 import BeautifulSoup

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
        return self.mod_name


class Downloader:
    count = 0

    def __init__(self, config: Config) -> None:
        self._config = config
        __class__.count += 1

    def __del__(self):
        __class__.count -= 1
        if __class__.count == 0:
            if os.path.exists('.download'):
                shutil.rmtree('.download')
            if os.path.exists('.temp'):
                shutil.rmtree('.temp')


    def _get_mod_id_from_url(self, mod_url: str) -> int:
        parsed_url = parse.urlparse(mod_url)
        qs = parse.parse_qs(parsed_url.query)
        return int(qs["id"][0])

    async def run(self) -> None:
        logger.info("%s: Получение id'шников модов..." % self._config.name)
        mod_ids = [self._get_mod_id_from_url(mod) for mod in self._config.mods]
        mod_info_pool = [self.get_mod_info(mod_id) for mod_id in mod_ids]

        logger.info("%s: Получение app_id модов..." % self._config.name)
        mod_infos = await asyncio.gather(*mod_info_pool)

        lock = asyncio.Lock()
        mod_download_links: Dict[str, str] = dict()

        logger.info(
            "%s: Получение ссылок на скачивание модов..." % self._config.name
        )
        await asyncio.wait(
            [
                self.get_download_link(mod_info, mod_download_links, lock)
                for mod_info in mod_infos
            ]
        )

        logger.info("%s: Скачивание модов..." % self._config.name)
        download_pool = []
        for filename, url in mod_download_links.items():
            download_pool.append(self._download_and_extract(url, filename))
        await asyncio.wait(download_pool)

    async def get_download_link(
        self, mod_info: ModInfo, out_dict: Dict[str, str], lock: asyncio.Lock
    ) -> None:
        data = {"item": mod_info.mod_id, "app": mod_info.app_id}
        headers = {"content-type": "application/x-www-form-urlencoded"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://steamworkshop.download/online/steamonline.php",
                data=data,
                headers=headers,
            ) as resp:
                response = await resp.text()
        soup = BeautifulSoup(response, "html.parser")
        url = soup.find("a").attrs["href"]
        async with lock:
            out_dict[mod_info.filename] = url

    async def get_mod_info(self, item_id: int) -> ModInfo:
        info_url = f"http://steamworkshop.download/download/view/{item_id}"

        response = requests.get(info_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        error_elem = soup.find("div", "basic_errors")
        if error_elem:
            raise ValueError(error_elem.text)

        links = soup.find_all("a")
        try:
            title_elem = next(filter(lambda x: "title" in x.attrs, links))
        except StopIteration:
            raise ValueError("Не удалость получить название")

        item_name: str = title_elem.attrs["title"]
        app_name: str = title_elem.next_element.next_element[2:-1]

        try:
            expr = r"({item: [0-9]*, app: [0-9]*})"
            data = re.search(expr, response.text)[0]  # type: ignore
            app_id: int = int(re.findall(r"[0-9]+", data)[1])  # type: ignore
        except IndexError:
            raise ValueError("Не удалось получить ID игры")

        return ModInfo(item_name, item_id, app_name, app_id)

    async def _download_and_extract(self, url: str, filename: str) -> None:
        mod_place_folder = Path(os.path.abspath(self._config.download_path))
        if not os.path.exists('.download'):
            os.mkdir('.download')
        filepath = ".".join((str(Path('.download') / filename), url.rsplit(".")[-1]))

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(filepath, mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        with ZipFile(filepath, 'r') as archive:
            # Extract all the contents of zip file in current directory
            archive.extractall('.temp')
            folder = archive.namelist()[0]

        shutil.move(Path('.temp') / folder, mod_place_folder / filename)
