from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import style

from .paths import Paths

style.use("ggplot")


def plot_as_path_size(as_id: str, counter: Counter[int]) -> Path:
    path_sizes = list(counter.keys())
    counts = list(counter.values())

    total_paths = sum(counts)
    mean_path_size = sum(size * count for size, count in counter.items()) / total_paths if total_paths != 0 else 0

    plt.figure(figsize=(10, 6))
    plt.bar(path_sizes, counts)

    plt.axvline(mean_path_size, color="black", linestyle='dashed', linewidth=1)
    plt.text(mean_path_size + 0.1, max(counts) * 0.8, f'Mean Path Size: {round(mean_path_size, 1)}')

    plt.xlabel("Path Sizes")
    plt.ylabel("Count")
    plt.title(f"Distribution of Path Sizes Originated from AS {as_id}")
    plt.xticks(path_sizes)
    plt.grid(True)

    save_path = Paths.CHART_DIR / f"{as_id}_path_size_dist.png"
    plt.savefig(save_path, dpi=300)
    plt.show()

    return save_path


def plot_multiple_as_path_sizes(as_data: dict[str, Counter[int]]) -> Path:
    all_path_sizes = sorted(set(size for counter in as_data.values() for size in counter.keys()))

    bar_width = 0.2
    indices = list(range(len(all_path_sizes)))

    plt.figure(figsize=(14, 8))

    for i, (as_id, counter) in enumerate(as_data.items()):
        counts = [counter.get(size, 0) for size in all_path_sizes]
        plt.bar([x + i * bar_width for x in indices], counts, bar_width, label=f'AS {as_id}')

    plt.xticks([x + bar_width * (len(as_data) - 1) / 2 for x in indices], all_path_sizes)

    plt.xlabel("Path Sizes")
    plt.ylabel("Count")
    plt.yscale('log')
    plt.title("Distribution of Path Sizes for Multiple ASs")
    plt.legend()
    plt.grid(True)

    save_path = Paths.CHART_DIR / "combined_path_size_dist.png"
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.show()

    return save_path


def cdf(data) -> str:
    plt.hist(data, normed=True, cumulative=True, label='CDF',
             histtype='step', alpha=0.8, color='k')

    save_path = Paths.CHART_DIR / f"cdf.png"
    plt.savefig(save_path, dpi=300)
    plt.show()
