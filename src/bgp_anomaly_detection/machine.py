from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from inspect import getmembers, isdatadescriptor
from json import dump as json_dump
from pathlib import Path
from pickle import dump
from typing import Iterable

import numpy as np
from scipy.stats import skew, norm

from .autonomous_system import AS
from .logging import Logger
from .mrt_file import SnapShot
from .paths import Paths

logger = Logger.get_logger(__name__)


class Machine:
    AS_PREDICT = {
        "location": {"got": str(), "expected": str(), "warning": int()},
        "mid_path_count": {"got": int(), "expected": float(), "warning": int()},
        "end_path_count": {"got": int(), "expected": float(), "warning": int()},
        "path_size": {"got": float(), "expected": float(), "warning": int()},
        "announced_prefixes": {"got": int(), "expected": float(), "warning": int()},
        "neighbours": {"got": int(), "expected": float(), "warning": int()},
    }

    __slots__ = ["dataset", "train_data"]

    def __init__(self) -> None:
        self.dataset: list[SnapShot] = list()
        self.train_data: dict[
            str, dict[
                str, tuple[
                    np.floating, np.floating, np.floating, np.floating, np.floating, np.floating | str
                ]
            ]
        ] = dict()

        self.train_data = dict()

    @staticmethod
    def _save_predictions(snapshot: SnapShot, predict: dict):
        predict_path = (Paths.PRED_DIR / str(snapshot)).with_suffix(".json")
        predictions_json = dict()

        for as_id in snapshot.as_map:
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

    def train(self, snapshots: SnapShot | Iterable[SnapShot]) -> None:
        """
        Trains the model using the provided snapshots of AS instances. This method updates historical data and computes
        statistical properties for each AS instance based on the provided snapshots.

        :param snapshots: A single snapshot or iterable of snapshots containing AS instances to train the model.
        :return: None
        """
        if not isinstance(snapshots, set):
            snapshots = set(snapshots)
        self.dataset = sorted(snapshots)

        # Initialize dictionaries and templates for storing AS history and statistical properties
        as_history = dict()
        as_special_property_names = ("id", "announced_prefixes", "neighbours")
        as_property_names = tuple(
            prty for prty, _ in getmembers(AS, isdatadescriptor)
            if prty not in as_special_property_names
        )
        as_history_template = {
            prty: list() for prty in as_property_names
        }
        as_property_stats_template = {
            prty: (
                np.float64(), np.float64(), np.float64(),
                np.float64(), np.float64(), np.float64(), str()
            ) for prty in as_property_names
        }

        logger.info(f"Starting training with {len(snapshots)} snapshots")

        for snapshot in self.dataset:
            # Update AS history for each AS in the snapshot
            for as_id, as_instance in snapshot.as_map.items():
                if as_id not in as_history:
                    as_history[as_id] = {
                        "history": deepcopy(as_history_template),
                        "announced_prefixes": set(),
                        "neighbours": set()
                    }
                # Update historical data for each AS property
                for property_ in as_property_names:
                    as_history[as_id]["history"][property_].append(getattr(as_instance, property_))
                as_history[as_id]["announced_prefixes"].update(as_instance.announced_prefixes)
                as_history[as_id]["neighbours"].update(as_instance.neighbours)

        # Compute statistics for each AS based on its history
        for as_id in as_history:
            data = as_history[as_id]
            self.train_data[as_id] = {
                "stats": deepcopy(as_property_stats_template),
                "announced_prefixes": as_history[as_id]["announced_prefixes"],
                "neighbours": as_history[as_id]["neighbours"]
            }
            # Compute statistics for each property of the current AS
            for prty in as_property_names:
                prty_history = data["history"][prty]
                if prty == "location":
                    mode = Counter(prty_history).most_common(1)[0][0]
                    self.train_data[as_id]["stats"][prty] = (
                        np.float64(-1), np.float64(-1), np.float64(-1),
                        np.float64(-1), np.float64(-1), np.float64(-1), mode
                    )
                    continue
                elif prty == "path_sizes":
                    counters = list()
                    for counter in prty_history:
                        for size, qnty in counter:
                            counters.extend(size for _ in range(qnty))
                    if counters:
                        prty_history = counters
                    else:
                        self.train_data[as_id]["stats"][prty] = (
                            np.float64(-1), np.float64(-1), np.float64(-1),
                            np.float64(-1), np.float64(-1), np.float64(-1), str()
                        )
                        continue
                # Compute range, mean, standard deviation, skewness, and slope for the current property data
                st_qt = np.percentile(prty_history, 25)
                rd_qt = np.percentile(prty_history, 75)
                dq = rd_qt - st_qt
                min_ = np.max((np.min(prty_history), st_qt - (1.5 * dq)))
                max_ = np.min((np.max(prty_history), rd_qt + (1.5 * dq)))
                mean = np.mean(prty_history)
                std_d = np.std(prty_history)
                if std_d > 0:
                    skewness = skew(np.array(prty_history))
                    slope, _ = np.polyfit(np.arange(len(prty_history)), prty_history, 1)
                else:
                    skewness = np.float64(0)
                    slope = np.float64(0)
                self.train_data[as_id]["stats"][prty] = (min_, max_, mean, std_d, skewness, slope, str())

        logger.info(f"Finished training")

    def predict(self, snapshot: SnapShot, save: bool = False) -> AS_PREDICT:

        predictions = dict()

        as_special_property_names = ("id", "announced_prefixes", "neighbours", "path_sizes")
        as_property_names = tuple(
            prty for prty, _ in getmembers(AS, isdatadescriptor)
            if prty not in as_special_property_names
        )
        as_prediction_template = {
            "warning_level": int(),
            "behaviour": int()
        }

        logger.info(f"Starting prediction for snapshot: {snapshot}")

        for as_id, as_instance in snapshot.as_map.items():
            if as_id not in self.train_data:
                predictions[as_id] = None
                continue
            else:
                predictions[as_id] = {prty: deepcopy(as_prediction_template) for prty in as_property_names}

            stats = self.train_data[as_id]["stats"]

            for prty in as_property_names:
                prty_predict = predictions[as_id][prty]
                value_to_validate = getattr(as_instance, prty)
                min_, max_, mean, std_d, skewness, slope, location = stats[prty]

                if prty == "location":
                    if value_to_validate != location:
                        prty_predict["warning_level"] += 2
                    continue

                if value_to_validate < min_ or value_to_validate > max_:
                    prty_predict["warning_level"] += 1

                if std_d > 0:
                    z_score = (value_to_validate - mean) / std_d
                    probability = norm.cdf(z_score)

                    if probability < 0.05 or probability > 0.95:
                        prty_predict["warning_level"] += 2

                threshold = 0.1
                if slope > threshold:
                    prty_predict["behaviour"] = 1
                elif slope < -threshold:
                    prty_predict["behaviour"] = -1
                else:
                    prty_predict["behaviour"] = 0

        logger.info(f"Finished prediction")

        if save:
            self._save_predictions(snapshot, predictions)

        return predictions

    # def export_csv(self, output_file: str | Path) -> None:
    #
    #     output_file = output_file.with_suffix(".csv")
    #
    #     logger.info(f"Exporting data to {output_file}")
    #
    #     csv_data = list()
    #     for as_id, as_instance in self.known_as.items():
    #         if as_instance._path_sizes.total() > 0:
    #             path_sizes = dumps(as_instance._path_sizes)
    #         else:
    #             path_sizes = None
    #         if as_instance._announced_prefixes:
    #             announced_prefixes = ";".join(as_instance._announced_prefixes)
    #         else:
    #             announced_prefixes = None
    #         if as_instance._neighbours:
    #             neighbours = ";".join(as_instance._neighbours)
    #         else:
    #             neighbours = None
    #
    #         csv_data.append({
    #             "as_id": as_id,
    #             "location": as_instance._location,
    #             "mid_path_count": as_instance._mid_path_count,
    #             "end_path_count": as_instance._end_path_count,
    #             "path_sizes": path_sizes,
    #             "announced_prefixes": announced_prefixes,
    #             "neighbours": neighbours
    #         })
    #
    #     with open(output_file, mode="w", newline="") as csv_file:
    #         fieldnames = [
    #             "as_id",
    #             "location",
    #             "mid_path_count",
    #             "end_path_count",
    #             "path_sizes",
    #             "announced_prefixes",
    #             "neighbours"
    #         ]
    #         writer = DictWriter(csv_file, fieldnames=fieldnames)
    #         writer.writeheader()
    #         writer.writerows(csv_data)
    #
    #     logger.info(f"Finished exporting")
    #
    # def export_txt(self, output_file: str | Path) -> None:
    #
    #     output_file = output_file.with_suffix(".txt")
    #
    #     logger.info(f"Exporting data to {output_file}")
    #
    #     with open(output_file, "w") as file:
    #         for as_id, as_instance in self.known_as.items():
    #             file.write(f"AS {as_id}:\n")
    #             file.write(f"  Times Seen: {as_instance.times_seen}\n")
    #             file.write(f"  Mid Path Count: {as_instance._mid_path_count}\n")
    #             file.write(f"  End Path Count: {as_instance._end_path_count}\n")
    #             file.write(f"  Path Sizes: {as_instance._path_sizes}\n")
    #             file.write(f"  Announced Prefixes: {', '.join(as_instance._announced_prefixes)}\n")
    #             file.write(f"  Neighbours: {', '.join(as_instance._neighbours)}\n")
    #             file.write("\n")
    #
    #     logger.info(f"Finished exporting")

    def save(self, output_file: str | Path) -> None:
        with open(output_file, 'wb') as file:
            dump(self, file)
        logger.info(f"Machine instance saved successfully at: {output_file}")

    # def plot_as_path_size(self, as_id: str | int) -> None:
    #     try:
    #         as_instance = self.known_as[str(as_id)]
    #     except KeyError:
    #         raise KeyError(f"Couldn't find any record of AS '{as_id}'")
    #
    #     logger.info(f"Plotting path size distribution for {as_instance}")
    #
    #     save_path = analyse.plot_as_path_size(as_instance._id, as_instance._path_sizes)
    #
    #     logger.info(f"Chart saved at {save_path}")
    #
    # def plot_multiple_as_path_size(self, *as_ids: str | int) -> None:
    #     as_data = dict()
    #     for as_id in as_ids:
    #         if str(as_id) in self.known_as:
    #             as_instance = self.known_as[str(as_id)]
    #             as_data[as_instance._id] = as_instance._path_sizes
    #         else:
    #             logger.info(f"Couldn't find any record of AS '{as_id}'")
    #
    #     logger.info(f"Plotting path size distribution for {tuple(str(self.known_as[_as]) for _as in as_data)}")
    #
    #     save_path = analyse.plot_multiple_as_path_sizes(as_data)
    #
    #     logger.info(f"Chart saved at {save_path}")
    #
    # def as_cdf(self, as_id: str | int) -> None:
    #     if isinstance(as_id, str) and not as_id.isnumeric():
    #         raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")
    #
    #     data = []
    #     as_instance = self.known_as[str(as_id)]
    #
    #     logger.info(f"Plotting cdf")
    #
    #     save_path = analyse.cdf(data)
    #     logger.info(f"Chart saved at {save_path}")


@dataclass(frozen=True, slots=True)
class Results:
    pass
