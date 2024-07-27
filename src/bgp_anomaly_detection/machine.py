from collections import Counter
from copy import deepcopy
from csv import writer
from dataclasses import dataclass
from pathlib import Path
from pickle import dump
from typing import Iterable

import numpy as np
from pandas import ExcelWriter, DataFrame
from scipy.stats import skew, norm

from .autonomous_system import AS
from .logging import Logger
from .mrt_file import SnapShot

logger = Logger.get_logger(__name__)


class Machine:
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
    def _save_predictions(snapshot: SnapShot, predictions: dict):

        formatted_timestamp = snapshot.timestamp.strftime("%Y%m%d.%H%M")
        i = 1
        while True:
            save_dir = Path("predict", formatted_timestamp + f"_{i:0>2}")
            if not save_dir.exists():
                break
            i += 1
        save_dir.mkdir()

        as_property_names = AS.get_property_names()
        csv_data = {prty: list() for prty in as_property_names}
        total_warning_level = list()

        for as_id, as_predictions in predictions.items():
            if as_predictions is None:
                for property_name in as_property_names:
                    csv_data[property_name].append((as_id, None, None))
                continue
            total_warning_level.append([as_id, int()])
            for property_name, property_prediction in as_predictions.items():
                csv_data[property_name].append((
                    as_id,
                    property_prediction["warning_level"],
                    property_prediction["behaviour"]
                ))
                total_warning_level[-1][1] += property_prediction["warning_level"]

        header1 = ("AS_ID", "Warning_Level")
        header2 = ("AS_ID", "Warning_Level", "Behaviour")
        with open(save_dir / "as_warning_level", mode="w", newline="") as csvfile:
            writer_ = writer(csvfile)
            writer_.writerow(header1)
            writer_.writerows(total_warning_level)
        for property_name in as_property_names:
            with open(save_dir / property_name, mode="w", newline="") as csvfile:
                writer_ = writer(csvfile)
                writer_.writerow(header2)
                writer_.writerows(csv_data[property_name])

        with ExcelWriter(save_dir / "predict.xlsx", engine="openpyxl") as exc_writer:
            df_warning_levels = DataFrame(total_warning_level, columns=header1)
            df_warning_levels.to_excel(exc_writer, sheet_name="as_warning_levels", index=False)
            for property_name in as_property_names:
                df = DataFrame(csv_data[property_name], columns=header2)
                df.to_excel(exc_writer, sheet_name=property_name, index=False)

        logger.info(f"Predictions saved in {save_dir}")

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
        as_property_names = AS.get_property_names()
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

    def predict(self, snapshot: SnapShot, save: bool = True) -> dict:

        predictions = dict()

        as_property_names = AS.get_property_names()
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

                threshold = 0.2
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
