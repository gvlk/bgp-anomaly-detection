from collections import Counter
from csv import DictReader, DictWriter
from json import loads
from pathlib import Path
from pickle import load
from tempfile import TemporaryDirectory
from unittest import TestCase

from bgp_anomaly_detection import Machine, SnapShot


class TestMachine(TestCase):

    @staticmethod
    def sort_csv_by_id(csv_file: str | Path):
        with open(csv_file, "r", newline="") as f:
            reader = DictReader(f)
            sorted_rows = sorted(reader, key=lambda row: int(row["as_id"]))

        with open(csv_file, "w", newline="") as f:
            writer = DictWriter(f, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(sorted_rows)

    def setUp(self):
        self.machine = Machine()
        self.snapshots = {
            SnapShot(file_path) for file_path in Path("test_data").rglob("rib*")
        }

    def test_train(self):
        self.machine.train(self.snapshots)
        self.assertGreater(len(self.machine.known_as), 0, "Training did not populate known_as")
        self.assertGreater(len(self.machine.dataset), 0, "Training did not populate dataset")

    def test_predict(self):
        self.machine.train(self.snapshots)
        snapshot = next(iter(self.snapshots))
        prediction = self.machine.predict(snapshot, save=False)
        self.assertIsInstance(prediction, dict, "Prediction result is not a dictionary")
        self.assertGreater(len(prediction), 0, "Prediction result is empty")

        for as_id in snapshot.known_as:
            self.assertIn(as_id, prediction, f"AS ID {as_id} not in prediction results")
            self.assertIn("mean", prediction[as_id], "Missing 'mean' in prediction result")
            self.assertIn("difference", prediction[as_id], "Missing 'difference' in prediction result")

    def test_export_csv(self):
        with TemporaryDirectory() as tempdir:
            self.machine.train(self.snapshots)
            output_file = Path(tempdir) / "data.csv"
            self.machine.export_csv(output_file)

            expected_file = Path("test_data", "sample_data_sum.csv")

            self.sort_csv_by_id(output_file)
            self.sort_csv_by_id(expected_file)

            with open(output_file, "r") as output, open(expected_file, "r") as expected:
                reader_output = DictReader(output)
                reader_expected = DictReader(expected)

                self.assertEqual(
                    reader_output.line_num,
                    reader_expected.line_num,
                    "Files have different number of lines"
                )

                for output_line, expected_line in zip(reader_output, reader_expected):
                    output_path_sizes = (
                        Counter()) \
                        if output_line["path_sizes"] == "" \
                        else (
                        Counter({int(k): v for k, v in loads(output_line["path_sizes"]).items()})
                    )
                    expected_path_sizes = (
                        Counter()) \
                        if expected_line["path_sizes"] == "" \
                        else (
                        Counter({int(k): v for k, v in loads(expected_line["path_sizes"]).items()})
                    )
                    output_announced_prefixes = (
                        set(output_line["announced_prefixes"].split(";"))) \
                        if output_line["announced_prefixes"] != "" \
                        else (
                        set()
                    )
                    expected_announced_prefixes = (
                        set(expected_line["announced_prefixes"].split(";"))) \
                        if expected_line["announced_prefixes"] != "" \
                        else (
                        set()
                    )
                    output_neighbours = (
                        set(output_line["neighbours"].split(";"))) \
                        if output_line["neighbours"] != "" \
                        else (
                        set()
                    )
                    expected_neighbours = (
                        set(expected_line["neighbours"].split(";"))) \
                        if expected_line["neighbours"] != "" \
                        else (
                        set()
                    )
                    self.assertEqual(
                        output_line["as_id"],
                        expected_line["as_id"],
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )
                    self.assertEqual(
                        output_line["location"],
                        expected_line["location"],
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )
                    self.assertEqual(
                        output_line["mid_path_count"],
                        expected_line["mid_path_count"],
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )
                    self.assertEqual(
                        output_line["end_path_count"],
                        expected_line["end_path_count"],
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )
                    self.assertEqual(
                        output_path_sizes,
                        expected_path_sizes,
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )
                    self.assertEqual(
                        output_announced_prefixes,
                        expected_announced_prefixes,
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )
                    self.assertEqual(
                        output_neighbours,
                        expected_neighbours,
                        f"Mismatch found:\n{output_line}\n{expected_line}"
                    )

    def test_save(self):
        with TemporaryDirectory() as tempdir:
            self.machine.train(self.snapshots)
            save_path = Path(tempdir) / "machine.pkl"
            self.machine.save(save_path)

            self.assertTrue(save_path.exists(), "Save file was not created")

            with open(save_path, "rb") as file:
                loaded_machine = load(file)

            self.assertEqual(self.machine.known_as.keys(), loaded_machine.known_as.keys(), "Loaded known_as differs")
            self.assertEqual(self.machine.dataset, loaded_machine.dataset, "Loaded dataset differs")
