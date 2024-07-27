# TODO: montar um modulo de interface que contenha funções (sequências) que uso frequentemente
from datetime import datetime, timedelta
from pickle import load

import requests

from .logging import Logger
from .machine import Machine
from .mrt_file import SnapShot
from .paths import Paths

logger = Logger.get_logger(__name__)


def download_bgp_snapshots(start_date: datetime, end_date: datetime):
    if start_date.minute != 0:
        start_date = start_date.replace(minute=0, second=0, microsecond=0)
    if start_date.hour % 2 != 0:
        start_date -= timedelta(hours=1)

    if end_date.minute != 0:
        end_date = end_date.replace(minute=0, second=0, microsecond=0)
    if end_date.hour % 2 != 0:
        end_date -= timedelta(hours=1)

    save_dir = Paths.RAW_DIR / f"{start_date.strftime("%Y%m%d.%H%M")}-{end_date.strftime("%Y%m%d.%H%M")}"
    save_dir.mkdir(exist_ok=True, parents=True)

    current_date = start_date
    file_count = int()
    total_size = int()

    logger.info(
        f"Downloading files from {start_date.strftime('%d/%m/%Y %H:%M')} to {end_date.strftime('%d/%m/%Y %H:%M')}"
    )

    while current_date <= end_date:
        year_month = current_date.strftime("%Y.%m")
        date_time = current_date.strftime("%Y%m%d.%H%M")
        url = f"https://archive.routeviews.org/route-views3/bgpdata/{year_month}/RIBS/rib.{date_time}.bz2"

        file_name = f"rib.{date_time}.bz2"
        file_path = save_dir / file_name

        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        file.write(chunk)
                total_size += file_path.stat().st_size
                logger.info(f"Downloaded: {file_name}")
            else:
                logger.info(f"File not found: {url}")
        except Exception as e:
            logger.info(f"Error downloading {url}: {e}")
        else:
            file_count += 1

        current_date += timedelta(hours=2)

    total_size_gb = total_size / (1024 ** 3)
    logger.info(f"{file_count} files downloaded, total size: {total_size_gb:.2f} GB, saved at: {save_dir}")


def get_machine(name: str) -> Machine:
    logger.info(f"Loading '{name}' machine")
    machine_path = (Paths.MODEL_DIR / name).with_suffix(".pkl")
    with open(machine_path, "rb") as file:
        machine = load(file)
    return machine
