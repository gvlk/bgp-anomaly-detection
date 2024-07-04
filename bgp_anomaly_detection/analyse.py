import json
import logging
import os
import glob
from datetime import datetime
import matplotlib.pyplot as plt
from pandas import DataFrame
from pathlib import Path
from .logging import *


# data_folder = 'data/parsed/'
# periods = ("one_day", "one_month", "one_year")
# characteristics = ('times_seen', 'n_mid_path', 'n_end_path', 'mean_path_size', 'total_prefixes',
#                    'total_neighbours')
# for period in periods:
#     period_folder = data_folder
#     df = load_json_files(period_folder)
#     for characteristic in characteristics:
#         plot_evolution(df,
#                        characteristic,
#                        f'Evolution of {characteristic} over One Year',
#                        period_folder)

def load_json_files(data_folder: str | Path):
    logging.info(f"Loading data from: {data_folder}")

    json_files = glob.glob(os.path.join(data_folder, '*.json'))
    data = []

    for json_file in json_files:
        with open(json_file, 'r') as f:
            snapshot = json.load(f)
            snapshot_time = datetime.strptime(snapshot['snapshot_time'], '%d/%m/%Y %H:%M')
            for as_id, as_info in snapshot['as']['as_info'].items():
                as_info['snapshot_time'] = snapshot_time
                as_info['as_id'] = as_id
                as_info["mean_path_size"] = as_info["path"]["mean_path_size"]
                as_info["total_prefixes"] = as_info["prefix"]["total_prefixes"]
                as_info["total_neighbours"] = as_info["neighbour"]["total_neighbours"]
                del as_info["path"]
                del as_info["prefix"]
                del as_info["neighbour"]
                data.append(as_info)

    df = DataFrame(data)
    df.set_index('snapshot_time', inplace=True)
    return df


def plot_evolution(df: DataFrame, characteristic: str, title: str, save_folder: str | Path):
    logging.info(f"Plotting: {characteristic}")
    plt.figure(figsize=(10, 6))
    for as_id in df['as_id'].unique():
        as_df = df[df['as_id'] == as_id].copy()
        plt.plot(as_df.index, as_df[characteristic], label=f'AS {as_id}')

    plt.title(title)
    plt.xlabel('Time')
    plt.ylabel(characteristic)
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{save_folder}/{characteristic}")
