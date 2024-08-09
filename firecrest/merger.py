import pstats
import os
import sys
import glob


def merger(directory, print_stats=False, sortby="cumulative"):
    """
    Merge all the stats files in a directory and save the combined stats in a file

    :param directory: the directory containing the stats files
    :param print_stats: if True, print the stats
    :param sortby: the sorting criteria could be 'cumulative' or 'tottime' or 'ncalls'

    """

    if directory.split(".")[-1] == "prof":
        stats_files = [directory]
    else:
        stats_files = [
            file
            for file in glob.glob(directory + "/**", recursive=True)
            if (os.path.isfile(file) and file.split(".")[-1] == "prof")
        ]

    combined_stats = pstats.Stats(stats_files[0])

    for stats_file in stats_files[1:]:
        combined_stats.add(stats_file)

    combined_stats.strip_dirs()

    try:
        save_name = directory.rstrip("\\") + "_combined_sortby_" + sortby
        combined_stats.sort_stats(sortby)
        combined_stats.dump_stats(f"{save_name}.profile")

    except IndexError:
        print(f"could not save the profile in {save_name}.profile")

    if print_stats:
        combined_stats.print_stats()

    with open(f"{save_name}.txt", "w") as f:
        combined_stats.stream = f
        combined_stats.print_stats()

    return f"Total time: {combined_stats.total_tt:.6f} seconds"
