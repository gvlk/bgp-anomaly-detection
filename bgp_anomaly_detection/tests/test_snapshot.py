from collections import Counter
from csv import DictReader
from json import loads
from pathlib import Path
from random import randint
from unittest import TestCase

from bgp_anomaly_detection import SnapShot
from bgp_anomaly_detection.autonomous_system import AS

TEST_DATA_DIR = Path("test_data")


class TestSnapShot(TestCase):

    @staticmethod
    def read_csv(file_path):
        with open(file_path, mode='r', newline='') as file:
            reader = DictReader(file)
            return list(reader)

    def setUp(self):
        file_paths = {
            file_path for file_path in Path("test_data").rglob("rib*")
        }
        self.file_path1 = file_paths.pop()
        self.file_path2 = file_paths.pop()
        self.file_path3 = file_paths.pop()
        self.csv_data1 = self.read_csv(self.file_path1)
        self.csv_data2 = self.read_csv(self.file_path2)
        self.csv_data3 = self.read_csv(self.file_path3)
        self.snapshot1 = SnapShot(self.file_path1)
        self.snapshot2 = SnapShot(self.file_path2)
        self.snapshot3 = SnapShot(self.file_path3)

    def test_import_csv(self):
        for _ in range(3):
            random_row = self.csv_data1[randint(0, len(self.csv_data1) - 1)]

            row_id = random_row["as_id"]
            row_mid_path_count = int(random_row["mid_path_count"])
            row_end_path_count = int(random_row["end_path_count"])
            row_ipv4_count = int(random_row["ipv4_count"])
            row_ipv6_count = int(random_row["ipv6_count"])
            if random_row["path_sizes"] != "":
                row_path_sizes = Counter({int(k): v for k, v in loads(random_row["path_sizes"]).items()})
            else:
                row_path_sizes = Counter()
            if random_row["announced_prefixes"] != "":
                row_announced_prefixes = set(random_row['announced_prefixes'].split(";"))
            else:
                row_announced_prefixes = set()
            if random_row["neighbours"] != "":
                row_neighbours = set(random_row["neighbours"].split(";"))
            else:
                row_neighbours = set()

            self.assertIn(row_id, self.snapshot1.known_as)
            random_as = self.snapshot1.known_as[row_id]
            self.assertIsInstance(random_as, AS)

            self.assertEqual(random_as.mid_path_count, row_mid_path_count)
            self.assertEqual(random_as.end_path_count, row_end_path_count)
            self.assertEqual(random_as.ipv4_count, row_ipv4_count)
            self.assertEqual(random_as.ipv6_count, row_ipv6_count)
            self.assertEqual(random_as.path_sizes, row_path_sizes)
            self.assertEqual(random_as.announced_prefixes, row_announced_prefixes)
            self.assertEqual(random_as.neighbours, row_neighbours)

    def test_as_types(self):
        for _ in range(3):
            random_row = self.csv_data1[randint(0, len(self.csv_data1) - 1)]

            row_id = random_row["as_id"]
            random_as = self.snapshot1.known_as[row_id]

            self.assertIsInstance(random_as.mid_path_count, int)
            self.assertIsInstance(random_as.end_path_count, int)
            self.assertIsInstance(random_as.path_sizes, Counter)
            for key, value in random_as.path_sizes.items():
                self.assertIsInstance(key, int)
                self.assertIsInstance(value, int)
            self.assertIsInstance(random_as.announced_prefixes, set)
            for prefix in random_as.announced_prefixes:
                self.assertIsInstance(prefix, str)
            self.assertIsInstance(random_as.neighbours, set)
            for neighbour in random_as.neighbours:
                self.assertIsInstance(neighbour, str)

    def test_eq(self):
        snapshot1_copy = SnapShot(self.file_path1)
        self.assertEqual(self.snapshot1, snapshot1_copy)

    def test_hash(self):
        snapshot1_copy = SnapShot(self.file_path1)
        self.assertEqual(hash(self.snapshot1), hash(snapshot1_copy))

    def test_reset(self):
        self.snapshot1.reset()
        self.assertEqual(len(self.snapshot1.known_as), 0)
        self.assertIsNone(self.snapshot1.snapshot_time)
