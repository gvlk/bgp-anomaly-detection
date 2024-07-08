from collections import Counter
from csv import DictWriter
from json import dumps
from pathlib import Path
from pickle import load
from random import randint, random, choice, shuffle, choices
from typing import Any

from faker import Faker

from bgp_anomaly_detection import Paths

fake = Faker()


def generate_files(n_files: int, n_rows: int):
    as_ids: list[str] = list(str(randint(1000, 60000)) for _ in range(n_rows + 5))
    with open(Path("..", "..", Paths.DELEG_DIR / "locale.pkl"), "rb") as file:
        location_dict: dict[str, str] = load(file)
    as_locations: list[str] = choices(tuple(location_dict.values()), k=n_rows)
    as_locations = ["ZZ" if location == "" else location for location in as_locations]

    as_data: dict[str, dict[str, Any]] = dict()

    for i in range(n_files):
        shuffle(as_ids)
        available_ids = as_ids.copy()
        rows = list()

        print(f"Generating CSV table with {n_rows} rows...")

        for j in range(n_rows):

            as_id = choice(available_ids)
            as_location = choice(as_locations)
            available_ids.remove(as_id)
            times_seen = randint(2, 45)
            mid_path_count = randint(0, times_seen)
            end_path_count = times_seen - mid_path_count

            path_sizes = Counter({0: end_path_count + 1})
            while path_sizes.total() > end_path_count:
                path_sizes.clear()
                path_sizes = Counter({randint(1, 4): randint(1, 20) for _ in range(randint(0, 3))})

            ipv4_count = int()
            ipv6_count = int()
            announced_prefixes_set = set()
            while len(announced_prefixes_set) != path_sizes.total():
                if random() <= 0.7:
                    announced_prefixes_set.add(fake.ipv4() + "/24")
                    ipv4_count += 1
                else:
                    announced_prefixes_set.add(fake.ipv6() + "/32")
                    ipv6_count += 1

            neighbours_set = set()
            neighbours_set_len = randint(1, n_rows // 2)
            while len(neighbours_set) != neighbours_set_len:
                neighbour = choice(as_ids)
                if neighbour != as_id:
                    neighbours_set.add(neighbour)

            rows.append(
                {
                    "as_id": as_id,
                    "location": as_location if as_id not in as_data else as_data[as_id]["location"],
                    "mid_path_count": mid_path_count,
                    "end_path_count": end_path_count,
                    "path_sizes": dumps(path_sizes) if path_sizes.total() > 0 else None,
                    "announced_prefixes": ";".join(announced_prefixes_set) if announced_prefixes_set else None,
                    "neighbours": ";".join(neighbours_set) if neighbours_set else None,
                    "ipv4_count": ipv4_count,
                    "ipv6_count": ipv6_count
                }
            )

            if as_id in as_data:
                as_data[as_id]["mid_path_count"] += mid_path_count
                as_data[as_id]["end_path_count"] += end_path_count
                as_data[as_id]["path_sizes"].update(path_sizes)
                as_data[as_id]["announced_prefixes"].update(announced_prefixes_set)
                as_data[as_id]["neighbours"].update(neighbours_set)
                as_data[as_id]["ipv4_count"] += ipv4_count
                as_data[as_id]["ipv6_count"] += ipv6_count
            else:
                as_data[as_id] = {
                    "location": as_location,
                    "mid_path_count": mid_path_count,
                    "end_path_count": end_path_count,
                    "path_sizes": path_sizes,
                    "announced_prefixes": announced_prefixes_set,
                    "neighbours": neighbours_set,
                    "ipv4_count": ipv4_count,
                    "ipv6_count": ipv6_count
                }

        random_date = fake.past_datetime().strftime("%Y%m%d.%H%M")
        file_path = Path("test_data", "rib." + random_date + ".csv")
        with open(file_path, mode="w", newline="") as file:
            fieldnames = [
                "as_id",
                "location",
                "mid_path_count",
                "end_path_count",
                "path_sizes",
                "announced_prefixes",
                "neighbours",
                "ipv4_count",
                "ipv6_count"
            ]
            writer = DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        print(f"{file_path.name} generated successfully.")

    file_path = Path("test_data", f"sample_data_sum.csv")
    with open(file_path, mode="w", newline="") as file:
        fieldnames = [
            "as_id",
            "location",
            "mid_path_count",
            "end_path_count",
            "path_sizes",
            "announced_prefixes",
            "neighbours",
            "ipv4_count",
            "ipv6_count"
        ]
        writer = DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for as_id in as_data:
            path_sizes = (
                dumps(as_data[as_id]["path_sizes"]) if as_data[as_id]["path_sizes"].total() > 0 else None
            )
            announced_prefixes = (
                ";".join(as_data[as_id]["announced_prefixes"]) if as_data[as_id]["announced_prefixes"] else None
            )
            neighbours = (
                ";".join(as_data[as_id]["neighbours"]) if as_data[as_id]["neighbours"] else None
            )
            writer.writerow(
                {
                    "as_id": as_id,
                    "location": as_data[as_id]["location"],
                    "mid_path_count": as_data[as_id]["mid_path_count"],
                    "end_path_count": as_data[as_id]["end_path_count"],
                    "path_sizes": path_sizes,
                    "announced_prefixes": announced_prefixes,
                    "neighbours": neighbours,
                    "ipv4_count": as_data[as_id]["ipv4_count"],
                    "ipv6_count": as_data[as_id]["ipv6_count"]
                }
            )

    print(f"{file_path.name} generated successfully.")


def main() -> None:
    generate_files(3, 10)


if __name__ == '__main__':
    main()
