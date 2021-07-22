import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def make_archive():
    build_directory = "dist"
    export_archive_name = "steam-workshop-downloader"
    if not os.path.exists(build_directory):
        raise ValueError("Не найдена папка %s" % build_directory)
    if not os.path.isdir(build_directory):
        raise ValueError("%s - не папка" % build_directory)

    with ZipFile(f"{export_archive_name}.zip", "w", ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(build_directory):
            for file in files:
                path = Path(root) / file
                archive.write(path, Path(*path.parts[1:]))


if __name__ == "__main__":
    make_archive()
