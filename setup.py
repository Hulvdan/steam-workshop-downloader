import os
import shutil
from distutils.core import setup

import py2exe

setup(
    options={
        "py2exe": {
            "bundle_files": 1,
            "compressed": True,
        }
    },
    console=["main.py"],
    name="steam-workshop-downloader",
)

if not os.path.exists("steam-workshop-downloader/configs"):
    os.mkdir("steam-workshop-downloader/configs")
shutil.copy("configs/example.yml", "steam-workshop-downloader/configs")
shutil.copy("README.md", "steam-workshop-downloader/README.md")
