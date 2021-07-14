from typing import List


class Downloader:
    def __init__(self, download_path: str, mods_list: List[str]) -> None:
        self._download_path = download_path
        self._mods_list = mods_list
