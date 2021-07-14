import json
from dataclasses import dataclass
import re
from typing import Optional
from src.list_config import get_configs
import requests
from bs4 import BeautifulSoup

# from src.collection import get_id_from_url

item_url = r"https://steamcommunity.com/sharedfiles/filedetails/?id=2266952591&searchtext="


@dataclass
class ItemInfo:
    item_name: str
    item_id: int
    app_name: str
    app_id: int


def get_item_info(item_id: int) -> ItemInfo:
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


def get_download_link(item_id: int, app_id: int) -> str:
    data = {"item": item_id, "app": app_id}
    headers = {"content-type": "application/x-www-form-urlencoded"}
    response = requests.post(
        "http://steamworkshop.download/online/steamonline.php",
        data,
        headers,
    )
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find('a').attrs['href']


if __name__ == "__main__":
    # item_data = get_item_info(get_id_from_url(item_url))
    # dl = get_download_link(item_data.item_id, item_data.app_id)
    # print(f"{dl=}")
    print(get_configs())
