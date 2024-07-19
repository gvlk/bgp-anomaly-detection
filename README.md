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

### SnapShot

The SnapShot class represents a snapshot of BGP data, facilitating the import, processing, and export of AS routing
information. It handles various file formats and provides methods for exporting data to CSV, JSON, and pickle formats.

```python
from bgp_anomaly_detection import SnapShot

snapshot = SnapShot(file_path='path/to/bgp/data', msg_limit=10000)
snapshot.export_csv("path/to/output/folder")
```

### Machine Learning for Anomaly Detection

The Machine class is used for training a model based on BGP snapshots and predicting anomalies in new snapshots. The
machine can train on multiple snapshots, updating its internal state, and make predictions for new snapshots by
comparing observed AS path statistics against learned statistics.

```python
from pathlib import Path
from bgp_anomaly_detection import SnapShot, Machine

mrt_folder = Path("path/to/mrt/folder")
snapshots = [SnapShot(file) for file in mrt_folder.rglob("*.bz2")]

val_snapshot = SnapShot("path/to/snapshot")

machine = Machine()
machine.train(snapshots)
results = machine.predict(val_snapshot)
```