from collections import Counter
from ipaddress import ip_address, IPv4Address
from json import loads
from typing import Self, Any


class AS:
    __slots__ = [
        "_id", "_location", "_mid_path_count", "_end_path_count", "_path_sizes",
        "_announced_prefixes", "_neighbours"
    ]

    def __init__(self, as_id: str, location: str = "ZZ") -> None:
        try:
            id_ = int(as_id)
        except ValueError:
            raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")
        else:
            self._id: str = str(id_)

        self._location: str = location

        self._mid_path_count: int = int()
        self._end_path_count: int = int()
        self._path_sizes: Counter[int] = Counter()
        self._announced_prefixes: set[str] = set()
        self._neighbours: set[str] = set()

    def __str__(self) -> str:
        return (
            f"{self._id}: "
            f"{self._location}, "
            f"Mean Path Size of {round(self.mean_path_size, 1)}, "
            f"{self.total_prefixes} Prefixes, "
            f"{self.total_neighbours} Neighbours"
        )

    def __repr__(self) -> str:
        return (
            f"AS(id={self._id!r}, location={self._location!r}"
            f"mid_path_count={self._mid_path_count}, end_path_count={self._end_path_count}, "
            f"path_sizes={dict(self._path_sizes)}, "
            f"announced_prefixes={self._announced_prefixes}, "
            f"neighbours={self._neighbours})"
        )

    def __iadd__(self, other: Self) -> Self:
        if isinstance(other, AS):
            if self._id != other.id:
                raise RuntimeError(f"These instances do not represent the same AS: {self} | {other}")
            self._mid_path_count += other.mid_path_count
            self._end_path_count += other.end_path_count
            self._path_sizes.update(other.path_sizes)
            self._announced_prefixes.update(other.announced_prefixes)
            self._neighbours.update(other.neighbours)
            return self
        return NotImplemented

    def __eq__(self, other: Self) -> bool:
        if isinstance(other, AS):
            return self._id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self._id)

    @property
    def id(self) -> str:
        return self._id

    @property
    def location(self):
        return self._location

    @property
    def mid_path_count(self):
        return self._mid_path_count

    @property
    def end_path_count(self):
        return self._end_path_count

    @property
    def path_sizes(self):
        return self._path_sizes

    @property
    def announced_prefixes(self):
        return self._announced_prefixes

    @property
    def neighbours(self):
        return self._neighbours

    @property
    def times_seen(self):
        return self._mid_path_count + self._end_path_count

    @property
    def mean_path_size(self) -> float:
        """Calculate the mean path size for the AS."""
        total_paths = sum(self._path_sizes.values())
        if total_paths == 0:
            return 0.0
        weighted_sum = sum(size * count for size, count in self._path_sizes.items())
        return weighted_sum / total_paths

    @property
    def ipv4_count(self) -> int:
        return sum(
            1 for prefix in self._announced_prefixes
            if isinstance(ip_address(prefix.split('/')[0]), IPv4Address)
        )

    @property
    def ipv6_count(self) -> int:
        return sum(
            1 for prefix in self._announced_prefixes
            if not isinstance(ip_address(prefix.split('/')[0]), IPv4Address)
        )

    @property
    def total_prefixes(self) -> int:
        return len(self._announced_prefixes)

    @property
    def total_neighbours(self) -> int:
        return len(self._neighbours)

    def import_json(self, data: dict[str, Any]) -> None:
        """Organize and import AS data from a JSON section."""
        self._mid_path_count = int(data["path"]["mid_path_count"])
        self._end_path_count = int(data["path"]["end_path_count"])
        self._path_sizes = Counter({int(k): v for k, v in data["path"]["path_sizes"].items()})
        self._announced_prefixes = set(data["prefix"]["announced_prefixes"])
        self._neighbours = set(data["neighbour"]["neighbours"])

    def import_csv(self, data: dict[str, Any]) -> None:
        """Organize and import AS data from a CSV row."""
        self._mid_path_count = int(data["mid_path_count"])
        self._end_path_count = int(data["end_path_count"])
        self._path_sizes = (
            Counter()) \
            if data["path_sizes"] == "" \
            else (
            Counter({int(k): v for k, v in loads(data["path_sizes"]).items()})
        )
        self._announced_prefixes = (
            set(data["announced_prefixes"].split(";"))) \
            if data["announced_prefixes"] != "" \
            else (
            set()
        )
        self._neighbours = (
            set(data["neighbours"].split(";"))) \
            if data["neighbours"] != "" \
            else (
            set()
        )

    def export(self) -> dict[str, Any]:
        """Export AS data in a standardized format."""
        return {
            "location": self._location,
            "times_seen": self.times_seen,
            "path": {
                "mid_path_count": self._mid_path_count,
                "end_path_count": self._end_path_count,
                "mean_path_size": self.mean_path_size,
                "path_sizes": self._path_sizes
            },
            "prefix": {
                "total_prefixes": self.total_prefixes,
                "ipv4_count": self.ipv4_count,
                "ipv6_count": self.ipv6_count,
                "announced_prefixes": tuple(self._announced_prefixes)
            },
            "neighbour": {
                "total_neighbours": self.total_neighbours,
                "neighbours": tuple(self._neighbours)
            }
        }

    def reset(self):
        """Reset the AS statistics."""
        self._mid_path_count = int()
        self._end_path_count = int()
        self._path_sizes.clear()
        self._announced_prefixes.clear()
        self._neighbours.clear()
