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
import zipfile
from skimage.color import rgb2gray
import imghdr

# ---------- Helper: detect file type ----------
def detect_file_type(file):
    """
    Determine the file type of a Streamlit UploadedFile or BytesIO object.
    Returns extension: .jpg, .png, .jp2, .nd2, .zip, or None if unknown.
    """
    filename = getattr(file, "name", "")
    ext = os.path.splitext(filename)[1].lower()

    # Known extensions
    if ext in [".jpg", ".jpeg", ".png", ".jp2", ".nd2", ".zip"]:
        return ext

    # Try detecting image type from content
    try:
        if hasattr(file, "read"):
            pos = file.tell()
            header_bytes = file.read(32)
            file.seek(pos)
            img_type = imghdr.what(None, h=header_bytes)
            if img_type == "jpeg":
                return ".jpg"
            elif img_type == "png":
                return ".png"
            # Add JP2 detection if needed
    except:
        pass

    return None

# ---------- Process a single image file ----------
def process_image_file(file, folder_name=""):
    results = []
    try:
        filename = getattr(file, "name", "uploaded_file")
        ext = detect_file_type(file)

        if ext is None:
            return [{"File": filename, "Error": "Unsupported image type"}]

        # Save to temporary file if needed
        temp_path = None
        if hasattr(file, "getbuffer"):
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(file.getbuffer())
            temp_file.close()
            temp_path = temp_file.name
        else:
            temp_path = filename

        frames = []

        # ND2 images
        if ext == ".nd2":
            with ND2Reader(temp_path) as images:
                frames = [np.asarray(frame) for frame in images]

        # Regular images
        elif ext in [".jpg", ".jpeg", ".png", ".jp2"]:
            img = Image.open(temp_path)
            frames = [np.array(img)]

        # ZIP files containing images
        elif ext == ".zip":
            with zipfile.ZipFile(temp_path, "r") as zip_ref:
                for name in zip_ref.namelist():
                    inner_ext = os.path.splitext(name)[1].lower()
                    if inner_ext in [".nd2", ".jpg", ".jpeg", ".png", ".jp2"]:
                        with zip_ref.open(name) as f:
                            if inner_ext == ".nd2":
                                # Save ND2 from zip to temp file
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".nd2") as temp_nd2:
                                    temp_nd2.write(f.read())
                                    temp_nd2.close()
                                    with ND2Reader(temp_nd2.name) as images:
                                        frames.extend([np.asarray(frame) for frame in images])
                                    os.remove(temp_nd2.name)
                            else:
                                img = Image.open(f)
                                frames.append(np.array(img))

        # Process each frame
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

        # Delete temp file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    except Exception as e:
        results.append({"File": getattr(file, "name", str(file)), "Error": str(e)})

    return results

# ---------- Main function for Streamlit ----------
def run_analysis(uploaded_file_bytes_list):
    """
    Processes a list of uploaded files (JPG, JP2, ND2, ZIP) and returns:
    - results_df: pandas DataFrame
    - excel_bytes: Excel file in bytes
    - chart_fig: matplotlib figure
    """
    all_results = []

    for f in uploaded_file_bytes_list:
        results = process_image_file(f)
        all_results.extend(results)

    results_df = pd.DataFrame(all_results)

    # Create Excel bytes
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        results_df.to_excel(writer, index=False, sheet_name="Results")
    excel_bytes = excel_buffer.getvalue()

    # Optional chart
    chart_fig = None
    if not results_df.empty and "Percentage" in results_df.columns:
        chart_fig, ax = plt.subplots()
        results_df.groupby("File")["Percentage"].mean().plot(kind="bar", ax=ax)
        ax.set_ylabel("Scratch Area (%)")
        ax.set_title("Scratch Area by File")
        plt.tight_layout()

    return results_df, excel_bytes, chart_fig
