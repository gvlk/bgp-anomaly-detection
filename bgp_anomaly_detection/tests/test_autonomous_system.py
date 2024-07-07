from collections import Counter, OrderedDict
from unittest import TestCase

from bgp_anomaly_detection.autonomous_system import AS


class TestAS(TestCase):
    def setUp(self):
        self.as_1 = AS("123")
        self.as_2 = AS("456")
        self.as_3 = AS("123")

        self.as_1.mid_path_count = 2
        self.as_1.end_path_count = 3
        self.as_1.path_sizes = Counter({1: 2, 2: 3})
        self.as_1.announced_prefixes = {"1.1.1.0/24", "2.2.2.0/24"}
        self.as_1.neighbours = {"234", "345"}

        self.as_2.mid_path_count = 4
        self.as_2.end_path_count = 3
        self.as_2.path_sizes = Counter({2: 4, 3: 3})
        self.as_2.announced_prefixes = {"3.3.3.0/24", "4.4.4.0/24"}
        self.as_2.neighbours = {"567", "678"}

        self.as_3.mid_path_count = 5
        self.as_3.end_path_count = 6
        self.as_3.path_sizes = Counter({2: 3, 3: 8})
        self.as_3.announced_prefixes = {"5.5.5.0/24", "6.6.6.0/24"}
        self.as_3.neighbours = {"888", "999"}

    def tearDown(self):
        # Tear down resources if needed
        pass


class TestAttr(TestAS):
    def test_id(self):
        self.assertEqual(self.as_1.id, "123")
        self.assertEqual(self.as_2.id, "456")

    def test_valid_as_id(self):
        try:
            AS("123")
        except ValueError:
            self.fail("AS initialization raised ValueError unexpectedly")

    def test_invalid_as_id_non_numeric(self):
        with self.assertRaises(ValueError):
            AS("invalid_as_id")

    def test_invalid_as_id_empty_string(self):
        with self.assertRaises(ValueError):
            AS("")

    def test_invalid_as_id_special_characters(self):
        with self.assertRaises(ValueError):
            AS("AS#456")

    def test_invalid_as_id_non_ascii(self):
        with self.assertRaises(ValueError):
            AS("AS_éüß")

    def test_mid_path_count(self):
        self.assertEqual(self.as_1.mid_path_count, 2)
        self.assertEqual(self.as_2.mid_path_count, 4)

    def test_end_path_count(self):
        self.assertEqual(self.as_1.end_path_count, 3)
        self.assertEqual(self.as_2.end_path_count, 3)

    def test_path_sizes(self):
        self.assertEqual(self.as_1.path_sizes, Counter({1: 2, 2: 3}))
        self.assertEqual(self.as_2.path_sizes, Counter({2: 4, 3: 3}))

    def test_announced_prefixes(self):
        self.assertEqual(self.as_1.announced_prefixes, {"1.1.1.0/24", "2.2.2.0/24"})
        self.assertEqual(self.as_2.announced_prefixes, {"3.3.3.0/24", "4.4.4.0/24"})

    def test_neighbours(self):
        self.assertEqual(self.as_1.neighbours, {"234", "345"})
        self.assertEqual(self.as_2.neighbours, {"567", "678"})

    def test_path_count(self):
        self.assertEqual(
            self.as_1.mid_path_count + self.as_1.end_path_count, self.as_1.times_seen
        )
        self.assertEqual(
            self.as_1.mid_path_count + self.as_1.end_path_count, self.as_1.path_sizes.total()
        )
        self.assertEqual(
            self.as_2.mid_path_count + self.as_2.end_path_count, self.as_2.times_seen
        )
        self.assertEqual(
            self.as_2.mid_path_count + self.as_2.end_path_count, self.as_2.path_sizes.total()
        )


class TestMethod(TestAS):
    def test_times_seen(self):
        self.assertEqual(self.as_1.times_seen, 5)
        self.assertEqual(self.as_2.times_seen, 7)

    def test_mean_path_size(self):
        self.assertEqual(self.as_1.mean_path_size, (1 * 2 + 2 * 3) / 5)
        self.assertEqual(self.as_2.mean_path_size, (2 * 4 + 3 * 3) / 7)

    def test_mean_path_size_edge_cases(self):
        as_instance = AS("123")
        as_instance.import_json({
            "path": {
                "mid_path_count": 0,
                "end_path_count": 0,
                "path_sizes": {}
            },
            "prefix": {
                "announced_prefixes": []
            },
            "neighbour": {
                "neighbours": []
            }
        })
        self.assertEqual(as_instance.mean_path_size, 0.0)

    def test_total_prefixes(self):
        self.assertEqual(self.as_1.total_prefixes, 2)
        self.assertEqual(self.as_2.total_prefixes, 2)

    def test_total_neighbours(self):
        self.assertEqual(self.as_1.total_neighbours, 2)
        self.assertEqual(self.as_2.total_neighbours, 2)

    def test_eq(self):
        self.assertEqual(self.as_1, self.as_3)
        self.assertNotEqual(self.as_1, self.as_2)

    def test_eq_with_different_data(self):
        as_different_id = AS("789")
        as_different_id.mid_path_count = 2
        as_different_id.end_path_count = 3
        as_different_id.path_sizes = Counter({1: 2, 2: 3})
        as_different_id.announced_prefixes = {"1.1.1.0/24", "2.2.2.0/24"}
        as_different_id.neighbours = {"234", "345"}

        self.assertNotEqual(self.as_1, as_different_id)

    def test_hash_consistency(self):
        self.assertEqual(hash(self.as_1), hash(self.as_3))
        self.assertNotEqual(hash(self.as_1), hash(self.as_2))

    def test_hash_equality(self):
        as_1_copy = AS("123")
        as_1_copy.mid_path_count = 2
        as_1_copy.end_path_count = 3
        as_1_copy.path_sizes = Counter({1: 2, 2: 3})
        as_1_copy.announced_prefixes = {"1.1.1.0/24", "2.2.2.0/24"}
        as_1_copy.neighbours = {"234", "345"}

        self.assertEqual(hash(self.as_1), hash(as_1_copy))

    def test_iadd(self):
        self.as_1 += self.as_3
        self.assertEqual(self.as_1.mid_path_count, 7)
        self.assertEqual(self.as_1.end_path_count, 9)
        self.assertEqual(self.as_1.path_sizes, Counter({1: 2, 2: 6, 3: 8}))
        self.assertEqual(self.as_1.announced_prefixes, {"1.1.1.0/24", "2.2.2.0/24", "5.5.5.0/24", "6.6.6.0/24"})
        self.assertEqual(self.as_1.neighbours, {"234", "345", "888", "999"})

    def test_iadd_runtimeerror(self):
        with self.assertRaises(RuntimeError):
            self.as_1 += self.as_2

    def test_reset(self):
        self.as_1.reset()
        self.assertEqual(self.as_1.mid_path_count, 0)
        self.assertEqual(self.as_1.end_path_count, 0)
        self.assertEqual(self.as_1.path_sizes, Counter())
        self.assertEqual(self.as_1.announced_prefixes, set())
        self.assertEqual(self.as_1.neighbours, set())

    def test_import_json(self):
        data = {
            "path": {
                "mid_path_count": 5,
                "end_path_count": 5,
                "path_sizes": {"1": 3, "2": 7}
            },
            "prefix": {
                "announced_prefixes": ["5.5.5.0/24", "6.6.6.0/24"]
            },
            "neighbour": {
                "neighbours": ["789", "890"]
            }
        }
        self.as_1.import_json(data)
        self.assertEqual(self.as_1.mid_path_count, 5)
        self.assertEqual(self.as_1.end_path_count, 5)
        self.assertEqual(self.as_1.path_sizes, Counter({1: 3, 2: 7}))
        self.assertEqual(self.as_1.announced_prefixes, {"5.5.5.0/24", "6.6.6.0/24"})
        self.assertEqual(self.as_1.neighbours, {"789", "890"})

    def test_import_csv(self):
        csv_row = OrderedDict([
            ("as_id", "123"),
            ("mid_path_count", "5"),
            ("end_path_count", "5"),
            ("path_sizes", '{"1": 3, "2": 7}'),
            ("announced_prefixes", "5.5.5.0/24;6.6.6.0/24"),
            ("neighbours", "789;890")
        ])
        self.as_1.import_csv(csv_row)
        self.assertEqual(self.as_1.mid_path_count, 5)
        self.assertEqual(self.as_1.end_path_count, 5)
        self.assertEqual(self.as_1.path_sizes, Counter({1: 3, 2: 7}))
        self.assertEqual(self.as_1.announced_prefixes, {"5.5.5.0/24", "6.6.6.0/24"})
        self.assertEqual(self.as_1.neighbours, {"789", "890"})

    def test_export(self):
        export_data = self.as_1.export()
        expected_data = {
            "times_seen": 5,
            "path": {
                "mid_path_count": 2,
                "end_path_count": 3,
                "mean_path_size": 1.6,
                "path_sizes": Counter({1: 2, 2: 3})
            },
            "prefix": {
                "total_prefixes": 2,
                "announced_prefixes": ("1.1.1.0/24", "2.2.2.0/24")
            },
            "neighbour": {
                "total_neighbours": 2,
                "neighbours": ("234", "345")
            }
        }
        self.assertEqual(export_data["times_seen"], expected_data["times_seen"])
        self.assertEqual(export_data["path"], expected_data["path"])
        self.assertEqual(export_data["prefix"]["total_prefixes"], expected_data["prefix"]["total_prefixes"])
        self.assertEqual(export_data["neighbour"]["total_neighbours"], expected_data["neighbour"]["total_neighbours"])
        self.assertEqual(set(export_data["prefix"]["announced_prefixes"]),
                         set(expected_data["prefix"]["announced_prefixes"]))
        self.assertEqual(set(export_data["neighbour"]["neighbours"]), set(expected_data["neighbour"]["neighbours"]))

    def test_export_import_round_trip(self):
        original_data = {
            "path": {
                "mid_path_count": 5,
                "end_path_count": 5,
                "path_sizes": {"1": 3, "2": 7}
            },
            "prefix": {
                "announced_prefixes": ["5.5.5.0/24", "6.6.6.0/24"]
            },
            "neighbour": {
                "neighbours": ["789", "890"]
            }
        }
        as_instance = AS("123")
        as_instance.import_json(original_data)
        exported_data = as_instance.export()

        reimported_instance = AS("123")
        reimported_instance.import_json(exported_data)
        for slot in as_instance.__slots__:
            self.assertEqual(getattr(as_instance, slot), getattr(reimported_instance, slot))


class TestType(TestAS):
    def test_id_type(self):
        self.assertIsInstance(self.as_1.id, str)
        self.assertIsInstance(self.as_2.id, str)

    def test_mid_path_count_type(self):
        self.assertIsInstance(self.as_1.mid_path_count, int)
        self.assertIsInstance(self.as_2.mid_path_count, int)

    def test_end_path_count_type(self):
        self.assertIsInstance(self.as_1.end_path_count, int)
        self.assertIsInstance(self.as_2.end_path_count, int)

    def test_path_sizes_type(self):
        self.assertIsInstance(self.as_1.path_sizes, Counter)
        self.assertIsInstance(self.as_2.path_sizes, Counter)
        for key in self.as_1.path_sizes.keys():
            self.assertIsInstance(key, int)
        for value in self.as_1.path_sizes.values():
            self.assertIsInstance(value, int)
        for key in self.as_2.path_sizes.keys():
            self.assertIsInstance(key, int)
        for value in self.as_2.path_sizes.values():
            self.assertIsInstance(value, int)

    def test_announced_prefixes_type(self):
        self.assertIsInstance(self.as_1.announced_prefixes, set)
        self.assertIsInstance(self.as_2.announced_prefixes, set)
        for element in self.as_1.announced_prefixes:
            self.assertIsInstance(element, str)
        for element in self.as_2.announced_prefixes:
            self.assertIsInstance(element, str)

    def test_neighbours_type(self):
        self.assertIsInstance(self.as_1.neighbours, set)
        self.assertIsInstance(self.as_2.neighbours, set)
        for element in self.as_1.neighbours:
            self.assertIsInstance(element, str)
        for element in self.as_2.neighbours:
            self.assertIsInstance(element, str)

    def test_times_seen_type(self):
        self.assertIsInstance(self.as_1.times_seen, int)
        self.assertIsInstance(self.as_2.times_seen, int)

    def test_mean_path_size_type(self):
        self.assertIsInstance(self.as_1.mean_path_size, float)
        self.assertIsInstance(self.as_2.mean_path_size, float)

    def test_total_prefixes_type(self):
        self.assertIsInstance(self.as_1.total_prefixes, int)
        self.assertIsInstance(self.as_2.total_prefixes, int)

    def test_total_neighbours_type(self):
        self.assertIsInstance(self.as_1.total_neighbours, int)
        self.assertIsInstance(self.as_2.total_neighbours, int)
