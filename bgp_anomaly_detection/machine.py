from csv import DictWriter
from json import dump as json_dump, dumps
from pathlib import Path
from pickle import dump
from typing import Union, Iterable

from . import analyse
from .autonomous_system import AS
from .logging import Logger
from .mrt_file import SnapShot
from .paths import Paths

logger = Logger.get_logger(__name__)


class Machine:
    Results = dict[str, dict[str, dict]]

    def __init__(self) -> None:
        self.known_as: dict[str, AS] = dict()
        self.dataset: set[str] = set()

    @staticmethod
    def _save_predictions(snapshot: SnapShot, predict: dict):
        predict_path = (Paths.PRED_DIR / str(snapshot)).with_suffix(".json")
        predictions_json = dict()

        for as_id in snapshot.known_as:
            predictions_json[as_id] = dict()
            if as_id not in predict:
                predictions_json[as_id]["Data"] = "No data"
                continue

            sum_warning_level = 0
            for metric in predict[as_id]:
                real = predict[as_id][metric]["real"]
                expected = predict[as_id][metric]["expected"]
                warning = predict[as_id][metric]["warning"]
                sum_warning_level += warning
                predictions_json[as_id][metric.capitalize()] = {
                    "Real": real,
                    "Expected": expected,
                    "Warning": warning
                }
            predictions_json[as_id]["Summed Warning Level"] = sum_warning_level

        with open(predict_path, "w") as file:
            json_dump(predictions_json, file, indent=4)

        logger.info(f"Prediction saved at: {predict_path}")

    @staticmethod
    def _get_warning_level(real_value: int | float, expected_value: int | float) -> int:
        difference = abs((real_value - expected_value) / max(expected_value, 1))
        if 0.0 <= difference <= 1.50:
            return 0
        elif difference <= 3.0:
            return 1
        else:
            return 2

    def train(self, snapshots: Union[SnapShot, Iterable[SnapShot]]) -> None:

        if isinstance(snapshots, SnapShot):
            snapshots = (snapshots,)

        logger.info(f"Starting training with {len(snapshots)} snapshots")

        for snapshot in snapshots:
            if snapshot not in self.dataset:
                for as_id in snapshot.known_as:
                    if as_id not in self.known_as:
                        self.known_as[as_id] = snapshot.known_as[as_id]
                    else:
                        self.known_as[as_id] += snapshot.known_as[as_id]
                self.dataset.add(str(snapshot))

        logger.info(f"Finished training")

    def predict(self, snapshot: SnapShot, save: bool = True) -> Results:
        predict = {
            key: {
                "location": {"real": str(), "expected": str(), "warning": int()},
                "mid_path_count": {"real": int(), "expected": float(), "warning": int()},
                "end_path_count": {"real": int(), "expected": float(), "warning": int()},
                "path_size": {"real": float(), "expected": float(), "warning": int()},
                "announced_prefixes": {"real": int(), "expected": float(), "warning": int()},
                "neighbours": {"real": int(), "expected": float(), "warning": int()},
            }
            for key in self.known_as
        }
        snapshot_count = len(self.dataset)

        def update_predictions(as_id_, attr, real_value, expected_value):
            predict[as_id_][attr]["real"] = real_value
            predict[as_id_][attr]["expected"] = expected_value
            predict[as_id_][attr]["warning"] = self._get_warning_level(real_value, expected_value)

        logger.info(f"Starting prediction for snapshot: {snapshot}")

        for as_id, as_instance in snapshot.known_as.items():
            known_as_instance = self.known_as.get(as_id)
            if known_as_instance is None:
                continue

            real_location = as_instance.location
            expected_location = known_as_instance.location
            predict[as_id]["location"]["real"] = real_location
            predict[as_id]["location"]["expected"] = expected_location
            predict[as_id]["location"]["warning"] = 0 if real_location == expected_location else 2

            update_predictions(as_id, "mid_path_count", as_instance.mid_path_count,
                               known_as_instance.mid_path_count / snapshot_count)
            update_predictions(as_id, "end_path_count", as_instance.end_path_count,
                               known_as_instance.end_path_count / snapshot_count)
            update_predictions(as_id, "path_size", as_instance.mean_path_size,
                               known_as_instance.mean_path_size / snapshot_count)
            update_predictions(as_id, "announced_prefixes", as_instance.total_prefixes,
                               known_as_instance.total_prefixes / snapshot_count)
            update_predictions(as_id, "neighbours", as_instance.total_neighbours,
                               known_as_instance.total_neighbours / snapshot_count)

        logger.info(f"Finished prediction")

        if save:
            self._save_predictions(snapshot, predict)

        return predict

    def export_csv(self, output_file: str | Path) -> None:

        output_file = output_file.with_suffix(".csv")

        logger.info(f"Exporting data to {output_file}")

        csv_data = list()
        for as_id, as_instance in self.known_as.items():
            if as_instance.path_sizes.total() > 0:
                path_sizes = dumps(as_instance.path_sizes)
            else:
                path_sizes = None
            if as_instance.announced_prefixes:
                announced_prefixes = ";".join(as_instance.announced_prefixes)
            else:
                announced_prefixes = None
            if as_instance.neighbours:
                neighbours = ";".join(as_instance.neighbours)
            else:
                neighbours = None

            csv_data.append({
                "as_id": as_id,
                "location": as_instance.location,
                "mid_path_count": as_instance.mid_path_count,
                "end_path_count": as_instance.end_path_count,
                "path_sizes": path_sizes,
                "announced_prefixes": announced_prefixes,
                "neighbours": neighbours
            })

        with open(output_file, mode="w", newline="") as csv_file:
            fieldnames = [
                "as_id",
                "location",
                "mid_path_count",
                "end_path_count",
                "path_sizes",
                "announced_prefixes",
                "neighbours"
            ]
            writer = DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        logger.info(f"Finished exporting")

    def export_txt(self, output_file: str | Path) -> None:

        output_file = output_file.with_suffix(".txt")

        logger.info(f"Exporting data to {output_file}")

        with open(output_file, "w") as file:
            for as_id, as_instance in self.known_as.items():
                file.write(f"AS {as_id}:\n")
                file.write(f"  Times Seen: {as_instance.times_seen}\n")
                file.write(f"  Mid Path Count: {as_instance.mid_path_count}\n")
                file.write(f"  End Path Count: {as_instance.end_path_count}\n")
                file.write(f"  Path Sizes: {as_instance.path_sizes}\n")
                file.write(f"  Announced Prefixes: {', '.join(as_instance.announced_prefixes)}\n")
                file.write(f"  Neighbours: {', '.join(as_instance.neighbours)}\n")
                file.write("\n")

        logger.info(f"Finished exporting")

    def save(self, output_file: str | Path) -> None:
        with open(output_file, 'wb') as file:
            dump(self, file)
        logger.info(f"Machine instance saved successfully at: {output_file}")

    def plot_as_path_size(self, as_id: str | int) -> None:
        try:
            as_instance = self.known_as[str(as_id)]
        except KeyError:
            raise KeyError(f"Couldn't find any record of AS '{as_id}'")

        logger.info(f"Plotting path size distribution for {as_instance}")

        save_path = analyse.plot_as_path_size(as_instance.id, as_instance.path_sizes)

        logger.info(f"Chart saved at {save_path}")

    def plot_multiple_as_path_size(self, *as_ids: str | int) -> None:
        as_data = dict()
        for as_id in as_ids:
            if str(as_id) in self.known_as:
                as_instance = self.known_as[str(as_id)]
                as_data[as_instance.id] = as_instance.path_sizes
            else:
                logger.info(f"Couldn't find any record of AS '{as_id}'")

        logger.info(f"Plotting path size distribution for {tuple(str(self.known_as[_as]) for _as in as_data)}")

        save_path = analyse.plot_multiple_as_path_sizes(as_data)

        logger.info(f"Chart saved at {save_path}")

    def as_cdf(self, as_id: str | int) -> None:
        if isinstance(as_id, str) and not as_id.isnumeric():
            raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")

        data = []
        as_instance = self.known_as[str(as_id)]

        logger.info(f"Plotting cdf")

        save_path = analyse.cdf(data)
        logger.info(f"Chart saved at {save_path}")
