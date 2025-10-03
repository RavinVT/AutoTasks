import argparse
from app import StreamingAutoTasks
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import shutil


__version__: str = "1.0.0"


parser = argparse.ArgumentParser(
    description="This is a program that allows you to automate actions for streaming and content creation by automating the publishing of the info to discord!"
)

parser.add_argument(
    "--version", "-v",
    action="store_true",
    help="Shows the current version of the program"
)

args = parser.parse_args()



appdata = Path(os.getenv("APPDATA")) / "AutoTasks"
appdata.mkdir(parents=True, exist_ok=True)

appdata_env = Path(appdata / ".env")

def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(relative_path).absolute()

def copy_file_from_exe(filename: str, destination) -> None:
    """Copy a bundled file to a destination (supports Path or str)."""
    src = resource_path(filename)
    dest = Path(destination)   # allows both Path and str
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    print(f"[ AutoTasks ][ Copy ] Copied {src} -> {dest}")


if not (appdata.exists() and appdata_env.exists()):
    try:
        copy_file_from_exe(".env", appdata_env)
    except Exception as error:
        print(f"[ AutoTasks ][ Installer ] Failed to install: missing files, not all files could be found!\nError: {error}")
        sys.exit()


load_dotenv(appdata_env)


app = StreamingAutoTasks()
try:
    app.load()
    app.run(os.getenv("TOKEN"))
except Exception as error:
    print(f"[ AutoTasks ] Kill Exception: {error}")
finally:
    app.save()
    sys.exit()