
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


def process_nd2_file(file_path, index_start=1, folder_name=""):
    """Process a single ND2 file and return area results."""
    area_list = []
    try:
        with ND2Reader(file_path) as images:
            img = np.asarray(images[0])  # First image

        h, w = img.shape
        entropy_filtered_image = entropy(img, disk(5))
        threshold = threshold_otsu(entropy_filtered_image)
        Scratch = entropy_filtered_image < threshold

        plt.subplot(3, 3, index_start)
        plt.imshow(Scratch, cmap='gray')

        area = np.sum(Scratch == 1) * 100.0 / (h * w)
        binary = entropy_filtered_image <= threshold
        scratch_area = np.sum(binary == 1)

        area_list.append({
            'Sr. No.': index_start,
            'Name': f"{folder_name}_{os.path.basename(file_path)}",
            'Scratch Area': scratch_area,
            'Percentage': area
        })

    except Exception as e:
        print("Error processing file:", file_path)
        print("Error message:", str(e))
    
    return area_list


def run_analysis(input_path=None, uploaded_files=None):
    """
    Process uploaded files or a local folder.
    Returns: results_df, excel_bytes, chart_fig
    """
    all_results = []

    # Cloud / Web usage: uploaded_files provided
    if uploaded_files:
        index_counter = 1
        for f in uploaded_files:
            # Handle CSV
            if f.name.lower().endswith('.csv'):
                df = pd.read_csv(f)
                excel_bytes = _to_excel_bytes(df)
                return df, excel_bytes, None

            # Handle Excel
            elif f.name.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(f)
                excel_bytes = _to_excel_bytes(df)
                return df, excel_bytes, None

            # Handle ND2
            elif f.name.lower().endswith('.nd2'):
                # Save temp file for processing
                tmp_path = os.path.join("/tmp", f.name)
                with open(tmp_path, "wb") as tmp_f:
                    tmp_f.write(f.getbuffer())
                results = process_nd2_file(tmp_path, index_start=index_counter)
                all_results.extend(results)
                index_counter += 1

            else:
                raise ValueError(f"Unsupported file type: {f.name}")

        if all_results:
            results_df = pd.DataFrame(all_results)
            excel_bytes = _to_excel_bytes(results_df)
            return results_df, excel_bytes, plt.gcf()

        raise ValueError("No valid files found.")

    # Local usage: input_path provided
    elif input_path:
        index_counter = 1
        for file_path in glob.glob(os.path.join(input_path, "*.nd2")):
            results = process_nd2_file(file_path, index_start=index_counter)
            all_results.extend(results)
            index_counter += 1

        if all_results:
            results_df = pd.DataFrame(all_results)
            excel_bytes = _to_excel_bytes(results_df)
            return results_df, excel_bytes, plt.gcf()
        else:
            raise ValueError("No ND2 files found in the provided folder.")

    else:
        raise ValueError("No input provided.")
