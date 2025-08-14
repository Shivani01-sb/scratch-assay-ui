import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from skimage.filters.rank import entropy
from skimage.morphology import disk
from skimage.filters import threshold_otsu
from nd2reader import ND2Reader
from PIL import Image
import tifffile
import os

def process_image_file(file, folder_name=""):
    """
    Process a single image file (ND2, TIFF, JPG, JP2) and calculate scratch area
    Returns a list of dicts with results
    """
    results = []

    try:
        ext = os.path.splitext(file.name if hasattr(file, 'name') else str(file))[1].lower()
        frames = []

        if ext == ".nd2":
            with ND2Reader(file) as images:
                frames = [np.asarray(frame) for frame in images]
        elif ext in [".tif", ".tiff"]:
            img = tifffile.imread(file)
            frames = [img[i] for i in range(img.shape[0])] if img.ndim == 3 else [img]
        elif ext in [".jpg", ".jpeg", ".png", ".jp2"]:
            img = Image.open(file)
            frames = [np.array(img)]
        else:
            return [{"File": file.name if hasattr(file, 'name') else str(file),
                     "Error": f"Unsupported image type: {ext}"}]

        from skimage.color import rgb2gray  # Import here to avoid unused import warnings

        for idx, img in enumerate(frames):
            h, w = img.shape[:2]

            # Convert RGB to grayscale if needed
            if img.ndim == 3 and img.shape[2] in [3, 4]:
                img = rgb2gray(img)

            # Ensure image is uint8 for entropy calculation
            img_uint8 = (img * 255).astype(np.uint8) if img.dtype != np.uint8 else img

            ent_img = entropy(img_uint8, disk(5))
            thresh = threshold_otsu(ent_img)
            scratch_mask = ent_img < thresh
            scratch_area_pix = np.sum(scratch_mask)
            scratch_percentage = scratch_area_pix * 100.0 / (h * w)

            results.append({
                "File": f"{folder_name}_{file.name if hasattr(file, 'name') else os.path.basename(file)}",
                "Frame": idx + 1,
                "Scratch Area (pix²)": scratch_area_pix,
                "Percentage": scratch_percentage
            })

    except Exception as e:
        results.append({
            "File": file.name if hasattr(file, 'name') else str(file),
            "Error": str(e)
        })

    return results


def run_analysis(uploaded_files):
    """
    Main function for Streamlit integration.
    uploaded_files: list of uploaded files (file-like objects)
    Returns: results_df, excel_bytes, chart_fig
    """
    if not uploaded_files:
        return pd.DataFrame(), None, None

    all_results = []
    for f in uploaded_files:
        all_results.extend(process_image_file(f))

    # Convert results to DataFrame
    results_df = pd.DataFrame(all_results)

    # Prepare Excel
    excel_buffer = BytesIO()
    results_df.to_excel(excel_buffer, index=False)
    excel_bytes = excel_buffer.getvalue()

    # Generate chart: Scratch area per frame
    chart_fig = None
    if not results_df.empty and "Scratch Area (pix²)" in results_df.columns:
        chart_fig = plt.figure(figsize=(10, 5))
        for file_name, group in results_df.groupby("File"):
            plt.plot(group["Frame"], group["Scratch Area (pix²)"], marker='o', label=file_name)
        plt.title("Scratch Area per Frame")
        plt.xlabel("Frame")
        plt.ylabel("Scratch Area (pix²)")
        plt.legend()
        plt.tight_layout()

    return results_df, excel_bytes, chart_fig
