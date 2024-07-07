from csv import DictWriter
from json import dumps
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
    Results = dict[str, dict[str, float]]

    def __init__(self) -> None:
        self.known_as: dict[str, AS] = dict()
        self.dataset: set[str] = set()

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

        logger.info(f"Starting prediction for snapshot: {snapshot}")

        predict = {
            key: {
                "mean": float(),
                "difference": float()
            }
            for key in self.known_as
        }
        snapshot_count = len(self.dataset)
        for as_id, as_instance in snapshot.known_as.items():
            if as_id in self.known_as:
                times_seen_mean = self.known_as[as_id].times_seen / snapshot_count
                times_seen_diff = (as_instance.times_seen - times_seen_mean) / times_seen_mean
                predict[as_id]["mean"] = times_seen_mean
                predict[as_id]["difference"] = times_seen_diff

        logger.info(f"Finished prediction")

        if save:
            predict_path = Paths.PRED_DIR / str(snapshot)
            with open(predict_path, "w") as file:
                for as_id, as_instance in snapshot.known_as.items():
                    file.write(f"{str(as_instance)}\n")
                    if as_id in predict:
                        times_seen_mean = predict[as_id]["mean"]
                        times_seen_diff = predict[as_id]["difference"]
                        times_seen_mean_str = str(round(times_seen_mean, 2))
                        if times_seen_diff >= 0:
                            times_seen_diff_str = "+" + str(round(times_seen_diff, 2))
                        else:
                            times_seen_diff_str = str(round(times_seen_diff, 2))
                        file.write(f"  Times Seen: {times_seen_diff_str} from average: {times_seen_mean_str}\n")
                    else:
                        file.write(f"  No data\n")
                    file.write("\n")

            logger.info(f"Prediction saved at: {predict_path}")

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
                "mid_path_count": as_instance.mid_path_count,
                "end_path_count": as_instance.end_path_count,
                "path_sizes": path_sizes,
                "announced_prefixes": announced_prefixes,
                "neighbours": neighbours
            })

        with open(output_file, mode='w', newline='') as csv_file:
            fieldnames = [
                "as_id",
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

        logger.info(f"Chart saved at {save_path}")

    def as_cdf(self, as_id: str | int) -> None:
        if isinstance(as_id, str) and not as_id.isnumeric():
            raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")

        data = []
        as_instance = self.known_as[str(as_id)]

        logger.info(f"Plotting cdf")

        save_path = analyse.cdf(data)
        logger.info(f"Chart saved at {save_path}")
