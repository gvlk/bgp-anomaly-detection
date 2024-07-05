import bgp_anomaly_detection as bgpad
from bgp_anomaly_detection import Paths


def main():
    for file in Paths.RAW_DIR.rglob("*.bz2"):
        snapshot = bgpad.SnapShot(file)
        destination_dir = Paths.PICKLE_DIR / file.parent.name
        snapshot.export_pickle(destination_dir)


if __name__ == "__main__":
    main()
