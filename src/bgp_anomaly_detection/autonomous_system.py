from dataclasses import dataclass
from ipaddress import ip_address, IPv4Address
from typing import Self


@dataclass(frozen=True, slots=True)
class AS:
    id: str
    location: str
    mid_path_count: int
    end_path_count: int
    path_sizes: frozenset[tuple[int, int]]
    announced_prefixes: frozenset[str]
    neighbours: frozenset[str]

    def __post_init__(self) -> None:
        try:
            id_ = int(self.id)
        except ValueError:
            raise ValueError(f"Invalid AS identifier: '{self.id}' is not a valid integer.")
        else:
            object.__setattr__(self, 'id', str(id_))

    def __str__(self) -> str:
        return (
            f"{self.id}: "
            f"{self.location}, "
            f"Mean Path Size of {round(self.mean_path_size, 1)}, "
            f"{self.total_prefixes} Prefixes, "
            f"{self.total_neighbours} Neighbours"
        )

    def __eq__(self, other: Self) -> bool:
        if isinstance(other, AS):
            return self.id == other.id
        return False

    # def __hash__(self) -> int:
    #     return hash(self.id)

    @property
    def times_seen(self) -> int:
        return self.mid_path_count + self.end_path_count

    @property
    def mean_path_size(self) -> float:
        total_paths = sum(size_count[1] for size_count in self.path_sizes)
        if total_paths == 0:
            return 0.0
        weighted_sum = sum(size * count for size, count in self.path_sizes)
        return weighted_sum / total_paths

    @property
    def ipv4_count(self) -> int:
        return sum(
            1 for prefix in self.announced_prefixes
            if isinstance(ip_address(prefix.split('/')[0]), IPv4Address)
        )

    @property
    def ipv6_count(self) -> int:
        return sum(
            1 for prefix in self.announced_prefixes
            if not isinstance(ip_address(prefix.split('/')[0]), IPv4Address)
        )

    @property
    def total_prefixes(self) -> int:
        return len(self.announced_prefixes)

    @property
    def total_neighbours(self) -> int:
        return len(self.neighbours)

    def export_json(self) -> dict[str, str | int | float | tuple]:
        return {
            "location": self.location,
            "times_seen": self.times_seen,
            "path": {
                "mid_path_count": self.mid_path_count,
                "end_path_count": self.end_path_count,
                "mean_path_size": self.mean_path_size,
                "path_sizes": tuple(self.path_sizes)
            },
            "prefix": {
                "total_prefixes": self.total_prefixes,
                "ipv4_count": self.ipv4_count,
                "ipv6_count": self.ipv6_count,
                "announced_prefixes": tuple(self.announced_prefixes)
            },
            "neighbour": {
                "total_neighbours": self.total_neighbours,
                "neighbours": tuple(self.neighbours)
            }
        }
