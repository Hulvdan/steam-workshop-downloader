import os
import shutil
from distutils.core import setup

import py2exe  # noqa: F401

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

if not os.path.exists("dist/configs"):
    os.mkdir("dist/configs")
shutil.copy("configs/example.yml", "dist/configs")
shutil.copy("README.md", "dist/README.md")
