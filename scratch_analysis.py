import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from skimage.filters.rank import entropy
from skimage.morphology import disk
from skimage.filters import threshold_otsu
from nd2reader import ND2Reader
from PIL import Image
import os
import tempfile
from skimage.color import rgb2gray

# ---------- Existing image processing function ----------
def process_image_file(file, folder_name=""):
    results = []
    try:
        filename = getattr(file, "name", "uploaded_file")
        ext = os.path.splitext(filename)[1].lower()

        temp_path = None
        if isinstance(file, BytesIO):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(file.getbuffer())
            temp_file.close()
            temp_path = temp_file.name
        else:
            temp_path = filename

        frames = []
        if ext == ".nd2":
            with ND2Reader(temp_path) as images:
                frames = [np.asarray(frame) for frame in images]
        elif ext in [".jpg", ".jpeg", ".png", ".jp2"]:
            img = Image.open(temp_path)
            frames = [np.array(img)]
        else:
            results.append({"File": filename, "Error": f"Unsupported image type: {ext}"})
            return results

        for idx, img in enumerate(frames):
            h, w = img.shape[:2]
            if img.ndim == 3 and img.shape[2] in [3, 4]:
                img = rgb2gray(img)
            img_uint8 = (img * 255).astype(np.uint8) if img.dtype != np.uint8 else img
            ent_img = entropy(img_uint8, disk(5))
            thresh = threshold_otsu(ent_img)
            scratch_mask = ent_img < thresh
            scratch_area_pix = np.sum(scratch_mask)
            scratch_percentage = scratch_area_pix * 100.0 / (h * w)
            results.append({
                "File": f"{folder_name}_{filename}",
                "Frame": idx + 1,
                "Scratch Area (pix²)": scratch_area_pix,
                "Percentage": scratch_percentage
            })

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    except Exception as e:
        results.append({"File": getattr(file, "name", str(file)), "Error": str(e)})

    return results

# ---------- New wrapper function for Streamlit ----------
def run_analysis(uploaded_file_bytes_list):
    """
    Main function called by Streamlit app.
    Args:
        uploaded_file_bytes_list: list of BytesIO objects (uploaded files)
    Returns:
        results_df: pandas DataFrame with scratch analysis
        excel_bytes: Excel file as bytes
        chart_fig: matplotlib figure (optional)
    """
    all_results = []

    for f in uploaded_file_bytes_list:
        results = process_image_file(f)
        all_results.extend(results)

    # Convert to DataFrame
    results_df = pd.DataFrame(all_results)

    # Create Excel bytes
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        results_df.to_excel(writer, index=False, sheet_name="Results")
    excel_bytes = excel_buffer.getvalue()

    # Optional: create chart
    chart_fig = None
    if not results_df.empty and "Percentage" in results_df.columns:
        chart_fig, ax = plt.subplots()
        results_df.groupby("File")["Percentage"].mean().plot(kind="bar", ax=ax)
        ax.set_ylabel("Scratch Area (%)")
        ax.set_title("Scratch Area by File")
        plt.tight_layout()

    return results_df, excel_bytes, chart_fig
