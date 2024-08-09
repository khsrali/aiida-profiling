## plot the results
import matplotlib

# matplotlib.use("TkAgg")  # Use the TkAgg backend which supports GUI rendering
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from collections import defaultdict
import numpy as np


def all_in_one(
    path_,
    xcolum,
    ycolum,
    xlabel="X",
    ylabel="Y",
    title="All_in_one",
    save_name=None,
    export_ticks=False,
):

    files = glob.glob(f"{path_}*.csv")

    fig, ax = plt.subplots(figsize=(10, 10))

    width = 0.8 / len(files)

    for i, file in enumerate(files):
        df = pd.read_csv(file)

        ax.bar(
            np.arange(len(df)) + i * width,
            df[f"{ycolum}"],
            width=width,
            color=plt.cm.get_cmap("viridis")(i / len(files)),
            label=os.path.basename(file),
        )
        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)
    ax.set_title(title)

    ax.grid()
    ax.legend(title="Files", bbox_to_anchor=(1.05, 1), loc="upper left")
    xticks = df[f"{xcolum}"] if xcolum in df.columns else df.index
    plt.xticks(ticks=np.arange(len(df)) + width * (len(files) - 1) / 2, labels=xticks)
    plt.tight_layout()

    if save_name:
        plt.savefig(f"{path_}{save_name}")

    if export_ticks:
        with open(f"{path_}_labels.txt", "w") as f:
            f.write("X\tY\n")
            for x_label, y_label in zip(xticks, df[f"{ycolum}"]):
                f.write(f"{x_label}\t {y_label}\n")

    return fig, ax, plt
