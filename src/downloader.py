import asyncio
import re
from dataclasses import dataclass

import aiohttp
import requests
from bs4 import BeautifulSoup

from .list_config import Config


@dataclass
class ItemInfo:
    item_name: str
    item_id: int
    app_name: str
    app_id: int


class Downloader:
    def __init__(self, config: Config) -> None:
        self._config = config

    async def process(self) -> None:
        await asyncio.sleep(1)

    async def get_download_link(self, item_id: int, app_id: int) -> str:
        data = {"item": item_id, "app": app_id}
        headers = {"content-type": "application/x-www-form-urlencoded"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://steamworkshop.download/online/steamonline.php",
                data,
                headers,
            ) as resp:
                response = await resp.text()
        soup = BeautifulSoup(response, "html.parser")
        return soup.find("a").attrs["href"]

    async def get_item_info(self, item_id: int) -> ItemInfo:
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
            data = re.search(r"({item: [0-9]*, app: [0-9]*})", response.text)[0]
            app_id: int = int(re.findall(r"[0-9]+", data)[1])
        except IndexError:
            raise ValueError("Не удалось получить ID игры")

        return ItemInfo(item_name, item_id, app_name, app_id)
