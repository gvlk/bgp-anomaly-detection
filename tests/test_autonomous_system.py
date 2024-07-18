from unittest import TestCase
from bgp_anomaly_detection.autonomous_system import AS


class TestAS(TestCase):

    def setUp(self):
        self.as_data = {
            'id': '123',
            'location': 'TestLocation',
            'mid_path_count': 10,
            'end_path_count': 5,
            'path_sizes': frozenset([(3, 11), (5, 5)]),
            'announced_prefixes': frozenset(['192.0.2.0/24', '2001:db8::/32']),
            'neighbours': frozenset(['456', '789'])
        }
        self.as_instance = AS(**self.as_data)

    def test_id_validation(self):
        with self.assertRaises(ValueError):
            AS(id='abc', location='TestLocation', mid_path_count=10, end_path_count=5,
               path_sizes=frozenset(), announced_prefixes=frozenset(), neighbours=frozenset())

    def test_str(self):
        expected_str = (
            "123: TestLocation, Mean Path Size of 3.6, 2 Prefixes, 2 Neighbours"
        )
        self.assertEqual(str(self.as_instance), expected_str)

    def test_eq(self):
        as_instance_2 = AS(**self.as_data)
        self.assertTrue(self.as_instance == as_instance_2)
        self.assertFalse(self.as_instance == "NotAnASObject")

    def test_hash(self):
        as_instance_2 = AS(**self.as_data)
        self.assertEqual(hash(self.as_instance), hash(as_instance_2))

    def test_times_seen(self):
        self.assertEqual(self.as_instance.times_seen, 15)

    def test_mean_path_size(self):
        self.assertAlmostEqual(self.as_instance.mean_path_size, 3.625)

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
            'location': 'TestLocation',
            'times_seen': 15,
            'path': {
                'mid_path_count': 10,
                'end_path_count': 5,
                'mean_path_size': 3.625,
                'path_sizes': {3: 11, 5: 5}
            },
            'prefix': {
                'total_prefixes': 2,
                'ipv4_count': 1,
                'ipv6_count': 1,
                'announced_prefixes': ('192.0.2.0/24', '2001:db8::/32')
            },
            'neighbour': {
                'total_neighbours': 2,
                'neighbours': ('456', '789')
            }
        }
        self.assertDictEqual(self.as_instance.export_json(), expected_json)
