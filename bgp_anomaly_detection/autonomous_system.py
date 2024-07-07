from collections import Counter
from json import loads
from typing import Self, Any


class AS:
    __slots__ = [
        "_id", "mid_path_count", "end_path_count",
        "path_sizes", "announced_prefixes", "neighbours"
    ]

    def __init__(self, as_id: str) -> None:
        try:
            id_ = int(as_id)
        except ValueError:
            raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")
        else:
            self._id = str(id_)

        self.mid_path_count: int = int()
        self.end_path_count: int = int()
        self.path_sizes: Counter[int] = Counter()
        self.announced_prefixes: set[str] = set()
        self.neighbours: set[str] = set()
        # self.locale

    def __str__(self) -> str:
        return (
            f"{self.id}: "
            f"Mean Path Size {round(self.mean_path_size)}, "
            f"{self.total_prefixes} Prefixes, "
            f"{self.total_neighbours} Neighbours"
        )

    def __repr__(self) -> str:
        return (
            f"AS(id={self.id!r}, "
            f"mid_path_count={self.mid_path_count}, end_path_count={self.end_path_count}, "
            f"path_sizes={dict(self.path_sizes)}, "
            f"announced_prefixes={tuple(self.announced_prefixes)}, "
            f"neighbours={tuple(self.neighbours)})"
        )

    def __iadd__(self, other: Self) -> Self:
        if isinstance(other, AS):
            if self.id != other._id:
                raise RuntimeError(f"These instances do not represent the same AS: {self} | {other}")
            self.mid_path_count += other.mid_path_count
            self.end_path_count += other.end_path_count
            self.path_sizes.update(other.path_sizes)
            self.announced_prefixes.update(other.announced_prefixes)
            self.neighbours.update(other.neighbours)
            return self
        return NotImplemented

    def __eq__(self, other: Self) -> bool:
        if isinstance(other, AS):
            return self._id == other._id
        return False

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def id(self) -> str:
        return self._id

    @property
    def times_seen(self):
        return self.mid_path_count + self.end_path_count

    @property
    def mean_path_size(self) -> float:
        """Calculate the mean path size for the AS."""
        total_paths = sum(self.path_sizes.values())
        if total_paths == 0:
            return 0.0
        weighted_sum = sum(size * count for size, count in self.path_sizes.items())
        return weighted_sum / total_paths

    @property
    def ipv4_count(self) -> int:
        return 0

    @property
    def ipv6_count(self) -> int:
        return 0

    @property
    def total_prefixes(self) -> int:
        return len(self.announced_prefixes)

    @property
    def total_neighbours(self) -> int:
        return len(self.neighbours)

    def import_json(self, data: dict[str, Any]) -> None:
        """Organize and import AS data from a JSON section."""
        self.mid_path_count = int(data["path"]["mid_path_count"])
        self.end_path_count = int(data["path"]["end_path_count"])
        self.path_sizes = Counter({int(k): v for k, v in data["path"]["path_sizes"].items()})
        self.announced_prefixes = set(data["prefix"]["announced_prefixes"])
        self.neighbours = set(data["neighbour"]["neighbours"])

    def import_csv(self, data: dict[str, Any]) -> None:
        """Organize and import AS data from a CSV row."""
        self.mid_path_count = int(data["mid_path_count"])
        self.end_path_count = int(data["end_path_count"])
        self.path_sizes = (
            Counter()) \
            if data["path_sizes"] == "" \
            else (
            Counter({int(k): v for k, v in loads(data["path_sizes"]).items()})
        )
        self.announced_prefixes = (
            set(data["announced_prefixes"].split(";"))) \
            if data["announced_prefixes"] != "" \
            else (
            set()
        )
        self.neighbours = (
            set(data["neighbours"].split(";"))) \
            if data["neighbours"] != "" \
            else (
            set()
        )

    def export(self) -> dict[str, Any]:
        """Export AS data in a standardized format."""
        return {
            "times_seen": self.times_seen,
            "path": {
                "mid_path_count": self.mid_path_count,
                "end_path_count": self.end_path_count,
                "mean_path_size": self.mean_path_size,
                "path_sizes": self.path_sizes
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

    def reset(self):
        """Reset the AS statistics."""
        self.mid_path_count = int()
        self.end_path_count = int()
        self.path_sizes.clear()
        self.announced_prefixes.clear()
        self.neighbours.clear()
