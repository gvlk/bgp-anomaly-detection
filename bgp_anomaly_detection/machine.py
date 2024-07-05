from typing import Union, Iterable
from pathlib import Path
from pickle import dump
from .logging import *
from .mrt_file import SnapShot
from .autonomous_system import AS
from .paths import Paths


class Machine:

    def __init__(self):
        self.known_as: dict[str, AS] = dict()

    def train(self, snapshots: Union[SnapShot, Iterable[SnapShot]]):

        if isinstance(snapshots, SnapShot):
            snapshots = (snapshots,)

        logging.info(f"Starting training with snapshots: {snapshots}")

        for snapshot in snapshots:
            for as_id in snapshot.known_as:
                if as_id not in self.known_as:
                    self.known_as[as_id] = snapshot.known_as[as_id]
                else:
                    self.known_as[as_id] += snapshot.known_as[as_id]

        with open('as_sum.txt', 'w') as file:
            predict_path = Paths.PRED_DIR / str(snapshot)
            for as_id, as_instance in self.known_as.items():
                file.write(f"AS {as_id}:\n")
                file.write(f"  Times Seen: {as_instance.times_seen}\n")
                file.write(f"  Mid Path Count: {as_instance.n_mid_path}\n")
                file.write(f"  End Path Count: {as_instance.n_end_path}\n")
                file.write(f"  Path Sizes: {as_instance.path_sizes}\n")
                file.write(f"  Announced Prefixes: {', '.join(as_instance.announced_prefixes)}\n")
                file.write(f"  Neighbours: {', '.join(as_instance.neighbours)}\n")
                file.write("\n")

        logging.info(f"Finished training")

    def predict(self, snapshot: SnapShot):
        logging.info(f"Starting prediction for snapshot: {snapshot}")

        with open('as_predict.txt', 'w') as file:
            for as_id, as_instance in snapshot.known_as.items():
                file.write(f"AS {as_id}:\n")

                if as_id in self.known_as:
                    times_seen_mean = self.known_as[as_id].times_seen / 2
                    times_seen_diff = round((as_instance.times_seen - times_seen_mean) / times_seen_mean, 2)

                    if times_seen_diff >= 0:
                        times_seen_diff = "+" + str(times_seen_diff)
                    else:
                        times_seen_diff = str(times_seen_diff)

                    file.write(f"  Times Seen: {times_seen_diff} from average\n")
                    file.write("\n")
                else:
                    file.write(f"No data\n")

        logging.info(f"Finished prediction")

    def save(self):
        save_path = Path("model", "machine.pkl")
        save_path = Paths.MODEL_DIR / "machine.pkl"
        with open(save_path, 'wb') as file:
            dump(self, file)
        logging.info(f"Machine instance saved successfully at: {save_path}")

