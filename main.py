from pathlib import Path
from bgp_anomaly_detection import *


def main():
    raw_folder = Path("data", "raw")
    raw_one_day_folder = raw_folder / "one_day"
    raw_one_month_folder = raw_folder / "one_month"
    raw_one_year_folder = raw_folder / "one_year"
    parsed_folder = Path("data", "parsed")
    parsed_one_day_folder = parsed_folder / "one_day"
    parsed_one_month_folder = parsed_folder / "one_month"
    parsed_one_year_folder = parsed_folder / "one_year"

    snapshots_train: set[SnapShot] = set()
    snapshots_predict: SnapShot | None = None

    for file in raw_one_day_folder.iterdir():
        snapshot = SnapShot(file)
        exit()
        snapshots_train.add(snapshot)
        snapshot.export_json(parsed_one_day_folder)

    for file in raw_one_month_folder.iterdir():
        snapshot = SnapShot(file)
        snapshots_train.add(snapshot)
        snapshot.export_json(parsed_one_month_folder)

    for file in raw_one_year_folder.iterdir():
        snapshot = SnapShot(file)
        snapshots_train.add(snapshot)
        snapshot.export_json(parsed_one_year_folder)

    snapshots_predict = snapshots_train.pop()
    my_machine = Machine()
    my_machine.train(snapshots_train)
    my_machine.predict(snapshots_predict)
    my_machine.save()


if __name__ == '__main__':
    main()
