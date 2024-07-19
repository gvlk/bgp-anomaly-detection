import unittest
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock

from frozendict import frozendict

from bgp_anomaly_detection import SnapShot
from bgp_anomaly_detection.autonomous_system import AS
from bgp_anomaly_detection.mrt_file import MRTParser


class TestSnapShot(unittest.TestCase):

    @patch('bgp_anomaly_detection.mrt_file.MRTParser')
    @patch('pathlib.Path')
    def test_snapshot_init(self, mock_path, mock_mrtparser):
        mock_path.return_value.suffix.lower.return_value = ".bz2"
        mock_path.return_value.stem.split.return_value = ["snapshot", "20230716", "1200"]

        mock_mrtparser_instance = mock_mrtparser.return_value
        mock_mrtparser_instance.import_bz2.return_value = frozendict(
            {"1111": AS("1111", "US", 1, 2, frozenset(), frozenset(), frozenset())})

        snapshot = SnapShot(file_path="mock.bz2")

        self.assertEqual(snapshot.timestamp, datetime(2023, 7, 16, 12, 0))
        self.assertEqual(snapshot.as_map,
                         frozendict({"AS1": AS("AS1", "US", 1, 2, frozenset(), frozenset(), frozenset())}))

    @patch('builtins.open', new_callable=mock_open,
           read_data='{"snapshot_time": "16/07/2023 12:00", "as": {"as_total": 1, "as_info": {"AS1": {"location": '
                     '"US", "path": {"mid_path_count": 1, "end_path_count": 2, "path_sizes": []}, "prefix": {'
                     '"announced_prefixes": []}, "neighbour": {"neighbours": []}}}}}')
    @patch('bgp_anomaly_detection.mrt_file.MRTParser')
    @patch('pathlib.Path')
    def test_import_json(self, mock_path, mock_mrtparser):
        mock_path.return_value.suffix.lower.return_value = ".json"
        mock_path.return_value.stem.split.return_value = ["snapshot", "20230716", "1200"]

        mock_mrtparser_instance = mock_mrtparser.return_value
        mock_mrtparser_instance.import_json.return_value = frozendict(
            {"1111": AS("1111", "US", 1, 2, frozenset(), frozenset(), frozenset())})

        snapshot = SnapShot(file_path="mock.json")

        self.assertEqual(snapshot.timestamp, datetime(2023, 7, 16, 12, 0))
        self.assertEqual(snapshot.as_map,
                         frozendict({"1111": AS("1111", "US", 1, 2, frozenset(), frozenset(), frozenset())}))

    @patch('pathlib.Path')
    def test_export_csv(self, mock_path):
        mock_path.return_value.__truediv__.return_value = mock_path.return_value
        mock_path.return_value.stem = "mock"
        mock_path.return_value.suffix.lower.return_value = ".csv"

        as_map = frozendict({"AS1": AS("AS1", "US", 1, 2, frozenset(), frozenset(), frozenset())})
        snapshot = SnapShot(file_path="mock.csv")
        snapshot.__dict__['_as_map'] = as_map  # Bypass frozen attributes for testing

        with patch('builtins.open', new_callable=mock_open) as mock_file:
            snapshot.export_csv(destination_dir=".")

            mock_file.assert_called_once_with(mock_path.return_value, mode="w", newline="")
            handle = mock_file()
            handle.write.assert_called()  # Ensure some writing happened

    @patch('pathlib.Path')
    def test_export_json(self, mock_path):
        mock_path.return_value.__truediv__.return_value = mock_path.return_value
        mock_path.return_value.stem = "mock"
        mock_path.return_value.suffix.lower.return_value = ".json"

        as_map = frozendict({"AS1": AS("AS1", "US", 1, 2, frozenset(), frozenset(), frozenset())})
        snapshot = SnapShot(file_path="mock.json")
        snapshot.__dict__['_as_map'] = as_map  # Bypass frozen attributes for testing

        with patch('builtins.open', new_callable=mock_open) as mock_file:
            snapshot.export_json(destination_dir=".")

            mock_file.assert_called_once_with(mock_path.return_value, "w")
            handle = mock_file()
            handle.write.assert_called()  # Ensure some writing happened

    @patch('pathlib.Path')
    def test_export_pickle(self, mock_path):
        mock_path.return_value.__truediv__.return_value = mock_path.return_value
        mock_path.return_value.stem = "mock"
        mock_path.return_value.suffix.lower.return_value = ".pkl"

        as_map = frozendict({"1111": AS("1111", "US", 1, 2, frozenset(), frozenset(), frozenset())})
        snapshot = SnapShot(file_path="mock.pkl")
        snapshot.__dict__['_as_map'] = as_map  # Bypass frozen attributes for testing

        with patch('builtins.open', new_callable=mock_open) as mock_file:
            snapshot.export_pickle(destination_dir=".")

            mock_file.assert_called_once_with(mock_path.return_value, "wb")
            handle = mock_file()
            handle.write.assert_called()  # Ensure some writing happened


class TestMRTParser(unittest.TestCase):

    @patch('bgp_anomaly_detection.mrt_file.Reader')
    @patch('builtins.open', new_callable=mock_open)
    @patch('bgp_anomaly_detection.mrt_file.pickle_load')
    def test_import_bz2(self, mock_pickle_load, mock_file, mock_reader):
        mock_reader_instance = mock_reader.return_value
        mock_reader_instance.__iter__.return_value = iter([MagicMock(), MagicMock()])
        mock_pickle_load.return_value = frozendict({"AS1": "US"})

        parser = MRTParser()
        result = parser.import_bz2(file_path="mock.bz2", msg_limit=2)

        self.assertIsInstance(result, frozendict)
        self.assertTrue(mock_file.called)

    @patch('builtins.open', new_callable=mock_open,
           read_data='{"as": {"as_total": 1, "as_info": {"1111": {"location": "US", "path": {"mid_path_count": 1, '
                     '"end_path_count": 2, "path_sizes": []}, "prefix": {"announced_prefixes": []}, "neighbour": {'
                     '"neighbours": []}}}}}')
    def test_import_json(self, mock_file):
        result = MRTParser.import_json(file_path="mock.json")

        self.assertIsInstance(result, frozendict)
        self.assertTrue(mock_file.called)

    @patch('builtins.open', new_callable=mock_open,
           read_data='as_id,location,mid_path_count,end_path_count,path_sizes,announced_prefixes,neighbours\n1111,US,'
                     '1,2,"{}","",""')
    def test_import_csv(self, mock_file):
        result = MRTParser.import_csv(file_path="mock.csv")

        self.assertIsInstance(result, frozendict)
        self.assertTrue(mock_file.called)
