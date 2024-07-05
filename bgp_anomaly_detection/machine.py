from pathlib import Path
from pickle import dump
from typing import Union, Iterable

from .autonomous_system import AS
from .logging import Logger
from .mrt_file import SnapShot
from .paths import Paths

logger = Logger.get_logger(__name__)


class Machine:

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

    def predict(self, snapshot: SnapShot, save: bool = True) -> dict[str, float]:
        logger.info(f"Starting prediction for snapshot: {snapshot}")

        predict = {key: float() for key in self.known_as}
        snapshot_count = len(self.dataset)
        for as_id, as_instance in snapshot.known_as.items():
            if as_id in self.known_as:
                times_seen_mean = self.known_as[as_id].times_seen / snapshot_count
                times_seen_diff = (as_instance.times_seen - times_seen_mean) / times_seen_mean
                predict[as_id] = times_seen_diff

        logger.info(f"Finished prediction")

        if save:
            predict_path = Paths.PRED_DIR / str(snapshot)
            with open(predict_path, "w") as file:
                for as_id, as_instance in snapshot.known_as.items():
                    file.write(f"{str(as_instance)}\n")
                    if as_id in predict:
                        times_seen_diff = predict[as_id]
                        if times_seen_diff >= 0:
                            times_seen_diff_str = "+" + str(round(times_seen_diff, 2))
                        else:
                            times_seen_diff_str = str(round(times_seen_diff, 2))
                        file.write(f"  Times Seen: {times_seen_diff_str} from average\n")
                    else:
                        file.write(f"  No data\n")
                    file.write("\n")

            logger.info(f"Prediction saved at: {predict_path}")

        return predict

    def export_data(self, output_file: str | Path) -> None:

        logger.info(f"Exporting data to {output_file}")

        with open(output_file, "w") as file:
            for as_id, as_instance in self.known_as.items():
                file.write(f"AS {as_id}:\n")
                file.write(f"  Times Seen: {as_instance.times_seen}\n")
                file.write(f"  Mid Path Count: {as_instance.n_mid_path}\n")
                file.write(f"  End Path Count: {as_instance.n_end_path}\n")
                file.write(f"  Path Sizes: {as_instance.path_sizes}\n")
                file.write(f"  Announced Prefixes: {', '.join(as_instance.announced_prefixes)}\n")
                file.write(f"  Neighbours: {', '.join(as_instance.neighbours)}\n")
                file.write("\n")

        logger.info(f"Finished exporting")

    def save(self) -> None:
        save_path = Paths.MODEL_DIR / "machine.pkl"
        with open(save_path, 'wb') as file:
            dump(self, file)
        logger.info(f"Machine instance saved successfully at: {save_path}")
