from collections import Counter
from copy import deepcopy
from csv import DictWriter
from inspect import getmembers
from json import dump as json_dump, dumps
from pathlib import Path
from pickle import dump
from typing import Iterable

import numpy as np
from scipy.stats import skew

from . import analyse
from .autonomous_system import AS
from .logging import Logger
from .mrt_file import SnapShot
from .paths import Paths

logger = Logger.get_logger(__name__)


class Machine:
    Results = dict[str, dict[str, dict]]

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

    def train(self, snapshots: SnapShot | Iterable[SnapShot]) -> None:
        """
        Trains the model using the provided snapshots of AS instances. This method updates historical data and computes
        statistical properties for each AS instance based on the provided snapshots.

        :param snapshots: A single snapshot or iterable of snapshots containing AS instances to train the model.
        :return: None
        """
        if isinstance(snapshots, SnapShot):
            snapshots = (snapshots,)

        # Initialize dictionaries and templates for storing AS history and statistical properties
        as_history = dict()
        as_special_property_names = ("announced_prefixes", "neighbours")
        as_property_names = tuple(
            prty for prty, _ in getmembers(AS, lambda x: isinstance(x, property))
            if prty not in (("id",) + as_special_property_names)
        )
        as_history_template = {
            prty: list() for prty in as_property_names
        }
        as_property_stats_template = {
            prty: (
                np.float64(), np.float64(), np.float64(),
                np.float64(), np.float64(), np.float64()
            ) for prty in as_property_names
        }

        logger.info(f"Starting training with {len(snapshots)} snapshots")

        for snapshot in snapshots:
            if snapshot in self.dataset:
                continue
            self.dataset.append(snapshot)
            # Update AS history for each AS in the snapshot
            for as_id, as_instance in snapshot.known_as.items():
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
        self.dataset.sort()

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
                        np.float64(-1), np.float64(-1), mode
                    )
                    continue
                elif prty == "path_sizes":
                    counters = list()
                    for counter in prty_history:
                        counters.extend(counter.elements())
                    if counters:
                        prty_history = counters
                    else:
                        self.train_data[as_id]["stats"][prty] = (
                            np.float64(-1), np.float64(-1), np.float64(-1),
                            np.float64(-1), np.float64(-1), np.float64(-1)
                        )
                        continue
                # Compute range, mean, variance, skewness, and slope for the current property data
                st_qt = np.percentile(prty_history, 25)
                rd_qt = np.percentile(prty_history, 75)
                dq = rd_qt - st_qt
                min_ = np.max((np.min(prty_history), st_qt - (1.5 * dq)))
                max_ = np.min((np.max(prty_history), rd_qt + (1.5 * dq)))
                mean = np.mean(prty_history)
                variance = np.var(prty_history)
                if variance > 0:
                    skewness = skew(np.array(prty_history))
                    slope, _ = np.polyfit(np.arange(len(prty_history)), prty_history, 1)
                else:
                    skewness = np.float64(0)
                    slope = np.float64(0)
                self.train_data[as_id]["stats"][prty] = (min_, max_, mean, variance, skewness, slope)

        logger.info(f"Finished training")

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
