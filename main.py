from pathlib import Path
from bgp_anomaly_detection import *


def main():
    raw_folder = Path("data", "raw")
    one_day_folder = raw_folder / "one_day"
    one_month_folder = raw_folder / "one_month"
    one_year_folder = raw_folder / "one_year"

    ignore_file = one_day_folder / "rib.20230601.0000.bz2"
    for file in one_day_folder.iterdir():
        if file == ignore_file:
            continue
        snapshot = SnapShot(file)
        snapshot.export()
        exit()

    for file in one_month_folder.iterdir():
        snapshot = SnapShot(file)
        snapshot.export()

    for file in one_year_folder.iterdir():
        snapshot = SnapShot(file)
        snapshot.export()


if __name__ == '__main__':
    main()
