from pathlib import Path

#: Буфер в байтах для скачивания файлов с сервера.
DOWNLOAD_CHUNK_SIZE = 16 * 1024  # noqa: WPS432

#: Папка, в которой будут создаваться файлы кешей конфигураций модов,
#: хранящие информацию о дате последнего обновления модов.
CACHE_DIR = Path(".cache")

#: Путь к временной папке для скачивания модов, которая будет потом удалена.
TEMP_DOWNLOAD_PATH = Path(".temp")

#: Частота опроса сервера о скачивании мода.
#: Опрос будет повторяться, пока мод на сервере не скачается,
#: после чего он начнёт скачиваться во временную папку.
CHECK_STATUS_INTERVAL = 0.5  # секунды

#: Максимальное количество одновременно скачиваемых модов.
SIMULTANEOUS_DOWNLOAD_MAX_COUNT = 5

#: Ограничение времени скачивания чанка
#: размером `DOWNLOAD_CHUNK_SIZE` в секундах.
CHUNK_DOWNLOAD_TIMEOUT = 5

#: Общее ограничение времени скачивания мода.
FILE_DOWNLOAD_TOTAL_TIMEOUT = None
