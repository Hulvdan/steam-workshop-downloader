import asyncio

from src.downloader import Downloader
from src.list_config import get_configs

if __name__ == "__main__":
    configs = get_configs()
    downloaders = [Downloader(cfg) for cfg in configs]

    loop = asyncio.get_event_loop()
    pool = [downloader.process() for downloader in downloaders]
    loop.run_until_complete(asyncio.wait(pool))
    loop.close()

    print("done")
