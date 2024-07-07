from collections import Counter
from typing import Self, Any


class AS:
    __slots__ = [
        "id", "times_seen", "n_mid_path", "n_end_path",
        "path_sizes", "announced_prefixes", "neighbours"
    ]

    def __init__(self, as_id: str) -> None:
        try:
            int(as_id)
        except ValueError:
            raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")
        else:
            self.id = str(as_id)

        self.times_seen: int = int()
        self.n_mid_path: int = int()
        self.n_end_path: int = int()
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

    def __iadd__(self, as_instance: Self) -> Self:
        if isinstance(as_instance, AS):
            self.times_seen += as_instance.times_seen
            self.n_mid_path += as_instance.n_mid_path
            self.n_end_path += as_instance.n_end_path
            self.path_sizes.update(as_instance.path_sizes)
            self.announced_prefixes.update(as_instance.announced_prefixes)
            self.neighbours.update(as_instance.neighbours)
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

    def export(self) -> dict[str, Any]:
        """Export AS data in a standardized format."""
        return {
            "times_seen": self.times_seen,
            "path": {
                "n_mid_path": self.n_mid_path,
                "n_end_path": self.n_end_path,
                "mean_path_size": self.mean_path_size(),
                "path_sizes": self.path_sizes
            },
            "prefix": {
                "total_prefixes": len(self.announced_prefixes),
                "announced_prefixes": tuple(self.announced_prefixes)
            },
            "neighbour": {
                "total_neighbours": len(self.neighbours),
                "neighbours": tuple(self.neighbours)
            }
        }

    def reset(self):
        """Reset the AS statistics."""
        self.times_seen = int()
        self.n_mid_path = int()
        self.n_end_path = int()
        self.path_sizes.clear()
        self.announced_prefixes.clear()
        self.neighbours.clear()

    def mean_path_size(self) -> float:
        """Calculate the mean path size for the AS."""
        total_paths = sum(self.path_sizes.values())
        if total_paths == 0:
            return 0.0
        weighted_sum = sum(int(size) * count for size, count in self.path_sizes.items())
        return weighted_sum / total_paths
