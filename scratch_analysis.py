import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import os
import glob
import numpy as np
from skimage.filters.rank import entropy
from skimage.morphology import disk
from skimage.filters import threshold_otsu
from nd2reader import ND2Reader


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes for download."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    buf.seek(0)
    return buf.getvalue()


def process_images_in_folder(folder_path, folder_name=""):
    """Process all .nd2 images in the given folder (recursively)."""
    area_list = []
    i = 1

    for file in glob.glob(os.path.join(folder_path, '*.nd2')):
        print("Processing file:", file)
        try:
            with ND2Reader(file) as images:
                img = np.asarray(images[0])  # First image
            
            h, w = img.shape
            entropy_filtered_image = entropy(img, disk(5))
            threshold = threshold_otsu(entropy_filtered_image)
            Scratch = entropy_filtered_image < threshold

            plt.subplot(3, 3, i)
            i += 1
            plt.imshow(Scratch, cmap='gray')

            area = np.sum(Scratch == 1) * 100.0 / (h * w)
            binary = entropy_filtered_image <= threshold
            scratch_area = np.sum(binary == 1)
            print("Scratch area=", scratch_area, "pix²")

            area_list.append({
                'Sr. No.': i,
                'Name': f"{folder_name}_{os.path.basename(file)}",
                'Scratch Area': scratch_area,
                'Percentage': area
            })

        except Exception as e:
            print("Error processing file:", file)
            print("Error message:", str(e))
    
    # Process subfolders recursively
    for subfolder in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder)
        if os.path.isdir(subfolder_path):
            area_list.extend(process_images_in_folder(subfolder_path, f"{folder_name}_{subfolder}"))

    return area_list


def run_analysis(input_path=None, uploaded_files=None):
    """
    Main analysis entry point for both local and cloud usage.
    
    Args:
        input_path: Optional path to local folder/file for offline use.
        uploaded_files: Optional list of Streamlit UploadedFile objects for cloud use.
    Returns:
        results_df, excel_bytes, chart_fig
    """
    if uploaded_files:
        # Process uploaded files (Streamlit Cloud / Web)
        file = uploaded_files[0]
        
        # CSV/Excel handling
        if file.name.lower().endswith('.csv'):
            df = pd.read_csv(file)
            excel_bytes = _to_excel_bytes(df)
            return df, excel_bytes, None
        
        elif file.name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
            excel_bytes = _to_excel_bytes(df)
            return df, excel_bytes, None
        
        elif file.name.lower().endswith('.nd2'):
            # Save the uploaded ND2 to a temp file
            tmp_path = os.path.join("/tmp", file.name)
            with open(tmp_path, "wb") as f:
                f.write(file.getbuffer())
            
            area_list = process_images_in_folder(os.path.dirname(tmp_path))
            results_df = pd.DataFrame(area_list)
            excel_bytes = _to_excel_bytes(results_df)
            return results_df, excel_bytes, plt.gcf()
        
        else:
            raise ValueError("Unsupported file type. Please upload .csv, .xlsx, or .nd2")
    
    elif input_path:
        # Local mode: process a given folder path
        area_list = process_images_in_folder(input_path)
        results_df = pd.DataFrame(area_list)
        excel_bytes = _to_excel_bytes(results_df)
        return results_df, excel_bytes, plt.gcf()
    
    else:
        raise ValueError("No input provided.")
