import os
import re

def simplify_file_names(folder_path):
    # Updated pattern to include "total" in the file name
    pattern = re.compile(
        r"comparison_(\w+)_((?:total_)?\w+)_count_boxplot_over_time_filtered_0\.000_month_(\w+)_((?:total_)?\w+)_count_boxplot_over_time_filtered_0\.000_month_comparison\.png"
    )

    # Iterate over the files in the folder
    for file_name in os.listdir(folder_path):
        # Match the pattern to the file name
        match = pattern.match(file_name)
        if match:
            # Extract relevant parts from the file name
            month1, type1, month2, type2 = match.groups()

            # Construct a simplified file name
            simplified_name = f"comparison_{month1}_{type1}_to_{month2}_{type2}.png"

            # Get full paths
            old_path = os.path.join(folder_path, file_name)
            new_path = os.path.join(folder_path, simplified_name)

            # Handle file name conflicts by appending a unique suffix
            if os.path.exists(new_path):
                base_name, ext = os.path.splitext(simplified_name)
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(folder_path, f"{base_name}_{counter}{ext}")
                    counter += 1

            # Rename the file
            os.rename(old_path, new_path)
            print(f"Renamed: {file_name} -> {os.path.basename(new_path)}")

# Example usage
folder = "simplify"
simplify_file_names(folder)
