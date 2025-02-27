import pickle

from bgp_anomaly_detection import Paths, SnapShot, Machine

# 2906 / 53066 / 6939

def main():
    snapshot = SnapShot("data/parsed/val/rib.20240402.1200.json")
    machine: Machine
    with open(Paths.MODEL_DIR / "machine.pkl", "rb") as file:
        machine = pickle.load(file)
    result = machine.predict(snapshot, save=True)
    machine.as_path_size_chart(2906)
    result = machine.predict(snapshot, save=True)
    machine.as_path_size_chart(53066)
    result = machine.predict(snapshot, save=True)
    machine.as_path_size_chart(6939)


if __name__ == "__main__":
    main()
