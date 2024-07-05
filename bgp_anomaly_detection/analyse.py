from collections import Counter

import matplotlib.pyplot as plt
from matplotlib import style

from .paths import Paths

style.use("ggplot")


def path_size_chart(as_id: int, counter: Counter):
    # Convert any string keys in the counter to integers if possible
    counter = {int(k): v for k, v in counter.items()}

    path_sizes = list(counter.keys())
    counts = list(counter.values())

    total_paths = sum(counts)
    mean_path_size = sum(size * count for size, count in counter.items()) / total_paths if total_paths != 0 else 0

    plt.figure(figsize=(10, 6))
    plt.bar(path_sizes, counts)

    # Plot mean path size as a horizontal line
    plt.axhline(mean_path_size, linestyle='dashed', linewidth=1)
    plt.text(max(path_sizes) * 0.8, mean_path_size + 0.5, f'Mean Path Size: {round(mean_path_size, 1)}')

    plt.xlabel("Path Sizes")
    plt.ylabel("Count")
    plt.title(f"Distribution of Path Sizes in AS {as_id}")
    plt.xticks(path_sizes)
    plt.grid(True)

    save_path = Paths.CHART_DIR / f"{as_id}_path_size_dist.png"
    plt.savefig(save_path, dpi=300)
    plt.show()

    return save_path  # Return the path where the chart is saved
