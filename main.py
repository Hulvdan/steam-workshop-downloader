import asyncio

from src.downloader import Downloader
from src.game_cfg import get_configs
from src.logging import logger

if __name__ == "__main__":
    configs = get_configs()
    downloaders = [Downloader(cfg) for cfg in configs]

    loop = asyncio.get_event_loop()
    pool = [downloader.run() for downloader in downloaders]
    loop.run_until_complete(asyncio.wait(pool))
    loop.close()

    logger.info("Завершено!")
