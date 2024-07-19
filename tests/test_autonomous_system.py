import unittest
from dataclasses import FrozenInstanceError

from bgp_anomaly_detection.autonomous_system import AS


class TestAS(unittest.TestCase):
    def setUp(self):
        self.as_data = {
            'id': '12345',
            'location': 'US',
            'mid_path_count': 10,
            'end_path_count': 5,
            'path_sizes': frozenset({(3, 2), (2, 3)}),
            'announced_prefixes': frozenset({'192.0.2.0/24', '2001:db8::/32'}),
            'neighbours': frozenset({'12346', '12347'}),
        }
        self.as_instance = AS(**self.as_data)

    def test_initialization(self):
        self.assertEqual(self.as_instance.id, '12345')
        self.assertEqual(self.as_instance.location, 'US')
        self.assertEqual(self.as_instance.mid_path_count, 10)
        self.assertEqual(self.as_instance.end_path_count, 5)
        self.assertEqual(self.as_instance.path_sizes, frozenset({(3, 2), (2, 3)}))
        self.assertEqual(self.as_instance.announced_prefixes, frozenset({'192.0.2.0/24', '2001:db8::/32'}))
        self.assertEqual(self.as_instance.neighbours, frozenset({'12346', '12347'}))

    def test_invalid_id_initialization(self):
        with self.assertRaises(ValueError):
            AS(**{**self.as_data, 'id': 'invalid_id'})

    def test_post_init(self):
        self.assertEqual(self.as_instance.id, '12345')
        with self.assertRaises(FrozenInstanceError):
            # noinspection PyDataclass
            self.as_instance.id = '54321'

    def test_str(self):
        expected_str = "12345: US, Mean Path Size of 2.4, 2 Prefixes, 2 Neighbours"
        self.assertEqual(str(self.as_instance), expected_str)

    def test_eq(self):
        another_instance = AS(**self.as_data)
        self.assertEqual(self.as_instance, another_instance)
        different_instance = AS(**{**self.as_data, 'id': '54321'})
        self.assertNotEqual(self.as_instance, different_instance)

    def test_times_seen(self):
        self.assertEqual(self.as_instance.times_seen, 15)

    def test_mean_path_size(self):
        self.assertAlmostEqual(self.as_instance.mean_path_size, 2.4)

    def test_ipv4_count(self):
        self.assertEqual(self.as_instance.ipv4_count, 1)

    def test_ipv6_count(self):
        self.assertEqual(self.as_instance.ipv6_count, 1)

    def test_total_prefixes(self):
        self.assertEqual(self.as_instance.total_prefixes, 2)

    def test_total_neighbours(self):
        self.assertEqual(self.as_instance.total_neighbours, 2)

    def test_export_json(self):
        expected_json = {
            "location": 'US',
            "times_seen": 15,
            "path": {
                "mid_path_count": 10,
                "end_path_count": 5,
                "mean_path_size": 2.4,
                "path_sizes": ((3, 2), (2, 3))
            },
            "prefix": {
                "total_prefixes": 2,
                "ipv4_count": 1,
                "ipv6_count": 1,
                "announced_prefixes": ('192.0.2.0/24', '2001:db8::/32')
            },
            "neighbour": {
                "total_neighbours": 2,
                "neighbours": ('12346', '12347')
            }
        }
        self.assertEqual(self.as_instance.export_json(), expected_json)
