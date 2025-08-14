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
import tempfile

def process_image_file(file, folder_name=""):
    """
    Process a single uploaded image file (ND2, TIFF, JPG, JP2) and calculate scratch area.
    Works with Streamlit's uploaded BytesIO files.
    Returns a list of dicts with results.
    """
    results = []

    try:
        # Get filename safely
        filename = getattr(file, "name", "uploaded_file")
        ext = os.path.splitext(filename)[1].lower()

        # Save to a temporary file if needed
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
        elif ext in [".tif", ".tiff"]:
            img = tifffile.imread(temp_path)
            frames = [img[i] for i in range(img.shape[0])] if img.ndim == 3 else [img]
        elif ext in [".jpg", ".jpeg", ".png", ".jp2"]:
            img = Image.open(temp_path)
            frames = [np.array(img)]
        else:
            results.append({
                "File": filename,
                "Error": f"Unsupported image type: {ext}"
            })
            return results

        from skimage.color import rgb2gray

        for idx, img in enumerate(frames):
            h, w = img.shape[:2]

            # Convert RGB to grayscale if needed
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
        results.append({
            "File": getattr(file, "name", str(file)),
            "Error": str(e)
        })

    return results
