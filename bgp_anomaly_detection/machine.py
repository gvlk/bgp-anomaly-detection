from typing import Union, Iterable
from pathlib import Path
from pickle import dump
from .logging import *
from .mrt_file import SnapShot
from .autonomous_system import AS
from .logging import Logger
from .paths import Paths

logger = Logger.get_logger(__name__)


class Machine:

    def __init__(self) -> None:
        self.known_as: dict[str, AS] = dict()

    def train(self, snapshots: Union[SnapShot, Iterable[SnapShot]]):

        if isinstance(snapshots, SnapShot):
            snapshots = (snapshots,)

        logger.info(f"Starting training with {len(snapshots)} snapshots")

        for snapshot in snapshots:
            for as_id in snapshot.known_as:
                if as_id not in self.known_as:
                    self.known_as[as_id] = snapshot.known_as[as_id]
                else:
                    self.known_as[as_id] += snapshot.known_as[as_id]
        logger.info(f"Finished training")

        logger.info(f"Finished prediction")

        if save:
            predict_path = Paths.PRED_DIR / str(snapshot)
            logger.info(f"Prediction saved at: {predict_path}")
        logger.info(f"Exporting data to {output_file}")
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

    def save(self):
        save_path = Path("model", "machine.pkl")
        save_path = Paths.MODEL_DIR / "machine.pkl"
        with open(save_path, 'wb') as file:
            dump(self, file)
        logger.info(f"Machine instance saved successfully at: {save_path}")
