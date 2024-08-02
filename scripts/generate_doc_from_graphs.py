import glob
import os

# Get all png files in the directory
filepaths = glob.glob("results/performance_graphs/*.png")

# Write the updated contents back to README.md
with open("README.md", "r") as f:
    readme_file = f.read()
    # Open temp.md in write mode
    with open("temp.md", "w") as temp_file:
        for filepath in filepaths:
            filename = os.path.basename(filepath).split(".")[0]

            if f"### {filename}" in readme_file:
                continue

            temp_file.write(f"\n\n### {filename}\n")
            temp_file.write(f"![]({filepath})\n")

            # Add table from associated text file
            header_added = False
            with open(
                f"results/performance_graphs/{filename}_labels.txt", "r"
            ) as labels_file:
                for line in labels_file:
                    column_1, column_2 = line.strip().split("\t")
                    temp_file.write(f"| {column_1} | {column_2} |\n")
                    if not header_added:
                        temp_file.write("| --- | --- |\n")
                        header_added = True

            temp_file.write("\n\n")

# Read README.md and remove the section between "## Performance Graphs" and "## End Performance Graphs"
with open("README.md", "r") as readme_file:
    lines = readme_file.readlines()

start_index = lines.index("## End Performance Graphs")
del lines[start_index]

# Insert the contents of temp.md into README.md
with open("temp.md", "r") as temp_file:
    lines.insert(start_index + 1, temp_file.read())
    lines.append("## End Performance Graphs")

# Write the updated contents back to README.md
with open("README.md", "w") as readme_file:
    readme_file.writelines(lines)

# Remove temp.md
os.remove("temp.md")
