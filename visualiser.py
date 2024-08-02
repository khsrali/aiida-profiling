import matplotlib

matplotlib.use("TkAgg")  # Use the TkAgg backend which supports GUI rendering
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
from collections import defaultdict
import numpy as np

# Get a list of all files in the results folder
files = glob.glob("results/*.csv")

# Group files by initial name
file_groups = defaultdict(list)
for file in files:
    base_name = os.path.basename(file)
    initial_name = base_name.split("_")[0]
    file_groups[initial_name].append(file)

# For each group of files
for initial_name, group_files in file_groups.items():
    fig, ax = plt.subplots(figsize=(10, 10))

    # Width of each bar
    width = 0.8 / len(group_files)

    # For each file in the group
    for i, file in enumerate(group_files):
        # Read the file
        df = pd.read_csv(file)

        # Plot the total_time(s) column
        ax.bar(
            np.arange(len(df)) + i * width,
            df["ave_time_per_call(ms)"],
            width=width,
            color=plt.cm.get_cmap("viridis")(i / len(group_files)),
            label=os.path.basename(file),
        )
        ax.set_ylabel("Average Time per Call (ms)")
        ax.set_xlabel("Endpoints (check the table)")  # to be inserted
    # Set the title
    ax.set_title(initial_name)

    ax.grid()
    ax.legend(title="Files", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.xticks(
        ticks=np.arange(len(df)) + width * (len(group_files) - 1) / 2, labels=df.index
    )
    plt.tight_layout()
    plt.savefig(f"results/performance_graphs/{initial_name}.png")
    plt.show()
