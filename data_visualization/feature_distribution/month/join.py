import os
from PIL import Image

def join_images(image1_path, image2_path, output_path):
    """
    Joins two images side by side and saves the result.
    :param image1_path: Path to the first image.
    :param image2_path: Path to the second image.
    :param output_path: Path to save the resulting image.
    """
    try:
        # Open the images
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)

        # Ensure the heights are the same for both images
        height = max(img1.height, img2.height)
        img1 = img1.resize((img1.width, height), Image.Resampling.LANCZOS)
        img2 = img2.resize((img2.width, height), Image.Resampling.LANCZOS)

        # Create a new blank image with combined width
        combined_width = img1.width + img2.width
        combined_img = Image.new("RGB", (combined_width, height))

        # Paste the images side by side
        combined_img.paste(img1, (0, 0))
        combined_img.paste(img2, (img1.width, 0))

        # Save the resulting image
        combined_img.save(output_path)
        print(f"Saved combined image: {output_path}")
    except Exception as e:
        print(f"Error processing images {image1_path} and {image2_path}: {e}")

def batch_join_images(folder_path, prefix1, prefix2, output_prefix):
    """
    Joins pairs of images in a folder side by side.
    Assumes the images have names starting with `prefix1` and `prefix2`.
    :param folder_path: Path to the folder containing the images.
    :param prefix1: Prefix for the first set of images.
    :param prefix2: Prefix for the second set of images.
    :param output_prefix: Prefix for the output images.
    """
    # List all files in the folder
    files = sorted(os.listdir(folder_path))
    image_pairs = []

    # Match files with the prefixes
    for file in files:
        if file.startswith(prefix1) and file.endswith('.png'):
            corresponding_file = file.replace(prefix1, prefix2)
            if corresponding_file in files:
                image_pairs.append((file, corresponding_file))

    # Process each pair
    for img1, img2 in image_pairs:
        img1_path = os.path.join(folder_path, img1)
        img2_path = os.path.join(folder_path, img2)

        # Use both filenames to create a unique output name
        output_name = f"{output_prefix}_{os.path.splitext(img1)[0]}_{os.path.splitext(img2)[0]}_comparison.png"
        output_path = os.path.join(folder_path, output_name)

        join_images(img1_path, img2_path, output_path)

# Example usage:
if __name__ == "__main__":
    folder = "./"  # Change to your folder path
    prefix1 = "june"  # Prefix for the first set of images
    prefix2 = "august"  # Prefix for the second set of images
    output_prefix = "comparison"

    batch_join_images(folder, prefix1, prefix2, output_prefix)
