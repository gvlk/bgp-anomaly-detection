from pathlib import Path


class Paths:
    REL_ROOT = Path(__file__).resolve().parent.parent.parent
    DELEG_DIR = Path(__file__).resolve().parent / "data" / "delegated"
    CHART_DIR = REL_ROOT / "chart"
    DATA_DIR = REL_ROOT / "data"
    DUMP_DIR = DATA_DIR / "dumps"
    PARSED_DIR = DATA_DIR / "parsed"
    PARSED_DIR_D = PARSED_DIR / "one_day"
    PARSED_DIR_M = PARSED_DIR / "one_month"
    PARSED_DIR_Y = PARSED_DIR / "one_year"
    PARSED_DIR_VAL = PARSED_DIR / "val"
    PICKLE_DIR = DATA_DIR / "pickled"
    PICKLE_DIR_D = PICKLE_DIR / "one_day"
    PICKLE_DIR_M = PICKLE_DIR / "one_month"
    PICKLE_DIR_Y = PICKLE_DIR / "one_year"
    PICKLE_DIR_VAL = PICKLE_DIR / "val"
    RAW_DIR = DATA_DIR / "raw"
    RAW_DIR_D = RAW_DIR / "one_day"
    RAW_DIR_M = RAW_DIR / "one_month"
    RAW_DIR_Y = RAW_DIR / "one_year"
    RAW_DIR_VAL = RAW_DIR / "val"
    MODEL_DIR = REL_ROOT / "model"
    PRED_DIR = REL_ROOT / "predict"


def ensure_project_structure():
    for value in Paths.__dict__.values():
        if isinstance(value, Path):
            value.mkdir(exist_ok=True)
