from .logging import Logger
from .machine import Machine
from .mrt_file import SnapShot
from .paths import Paths, ensure_project_structure

ensure_project_structure()
Logger.setup_logging()
