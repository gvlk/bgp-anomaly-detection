# BGP Anomaly Detection

This project is aimed at detecting anomalies in BGP (Border Gateway Protocol) data using snapshot files. The primary
components of the system include the SnapShot class for handling BGP data files and the Machine class for training and
predicting based on the BGP snapshots.

BGP Snapshot File Archive: https://archive.routeviews.org/route-views3/bgpdata/

## Installation

```shell
pip install git+https://github.com/gvlk/bgp-anomaly-detection.git
```

## Usage

BGP Data SnapShot
The SnapShot class is responsible for handling raw BGP data files, parsing them, and exporting the parsed data into
various formats. The supported file formats include .bz2, .json, and .pkl.

```python
import bgp_anomaly_detection as bgpad
from bgp_anomaly_detection import Paths


def main():
    for file in Paths.RAW_DIR.rglob("*.bz2"):
        snapshot = bgpad.SnapShot(file)
        destination_dir = Paths.PICKLE_DIR / file.parent.name
        snapshot.export_pickle(destination_dir)


if __name__ == "__main__":
    main()
```

### SnapShot Class

The SnapShot class can handle BGP data in different formats:

- .bz2: Raw BGP data file
- .json: JSON file containing parsed AS data
- .pkl: Pickle file containing a previously saved SnapShot instance

The SnapShot class provides methods to import and export data, parse AS path data, and handle different BGP message
types.

### Machine Learning for Anomaly Detection

The Machine class is used for training a model based on BGP snapshots and predicting anomalies in new snapshots. The
machine can train on multiple snapshots, updating its internal state, and make predictions for new snapshots by
comparing observed AS path statistics against learned statistics.

```python
from bgp_anomaly_detection import Machine, SnapShot

machine = Machine()
```

### Train the machine with snapshots

```python
snapshots = [SnapShot(file) for file in Paths.PICKLE_DIR.rglob("*.pkl")]
machine.train(snapshots)
```

### Predict anomalies in a new snapshot

```python
new_snapshot = SnapShot("path/to/new_snapshot.bz2")
predictions = machine.predict(new_snapshot)
```

### Export the model data

```python
machine.export_txt("path/to/exported_data.txt")
```

### Save the machine state

```python
machine.save()
```

### Logging

Logging is used extensively throughout the project to track the progress and status of data processing, training, and
prediction tasks. This helps in debugging and understanding the workflow.

## Project Structure

- bgp_anomaly_detection/
    - __init__.py: Initialization of the module
    - autonomous_system.py: Contains the AS class representing an Autonomous System
    - logging.py: Custom logging utilities
    - paths.py: Paths configuration
    - mrt_file.py: Contains the SnapShot class
    - machine.py: Contains the Machine class
