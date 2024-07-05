from pathlib import Path


class Paths:
    CHART_DIR = Path("chart")
    DATA_DIR = Path("data")
    DUMP_DIR = DATA_DIR / "dumps"
    PARSED_DIR = DATA_DIR / "parsed"
    PARSED_DIR_D = PARSED_DIR / "one_day"
    PARSED_DIR_M = PARSED_DIR / "one_month"
    PARSED_DIR_Y = PARSED_DIR / "one_year"
    PICKLE_DIR = DATA_DIR / "pickled"
    PICKLE_DIR_D = PICKLE_DIR / "one_day"
    PICKLE_DIR_M = PICKLE_DIR / "one_month"
    PICKLE_DIR_Y = PICKLE_DIR / "one_year"
    RAW_DIR = DATA_DIR / "raw"
    RAW_DIR_D = RAW_DIR / "one_day"
    RAW_DIR_M = RAW_DIR / "one_month"
    RAW_DIR_Y = RAW_DIR / "one_year"
    MODEL_DIR = Path("model")
    PRED_DIR = Path("predict")


def ensure_project_structure():
    for value in Paths.__dict__.values():
        if isinstance(value, Path):
            value.mkdir(exist_ok=True)
