import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    buf.seek(0)
    return buf.getvalue()

def run_analysis(input_path=None, uploaded_files=None):
    """
    Args:
        input_path: Optional local path to data folder/file.
        uploaded_files: Optional list of Streamlit UploadedFile objects.
    Returns:
        results_df (pd.DataFrame), excel_bytes (bytes), chart_fig (plt.Figure or None)
    """
    # --- Load data ---
    if uploaded_files:
        # Example: take first file for now
        f = uploaded_files[0]
        if f.name.lower().endswith('.csv'):
            df = pd.read_csv(f)
        elif f.name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(f)
        else:
            raise ValueError("Unsupported file type.")
    elif input_path:
        # Original logic follows, with input_path in place of hardcoded paths
        pass  # placeholder to run original code
    else:
        raise ValueError("No input provided.")

    # --- Begin original logic ---
    import glob
    import numpy as np
    import os
    import pandas as pd
    from skimage.filters.rank import entropy
    from skimage.morphology import disk
    from skimage.filters import threshold_otsu
    from nd2reader import ND2Reader
    import matplotlib.pyplot as plt  # Importing matplotlib

    def process_images_in_folder(folder_path, folder_name=""):
        area_list = []
        i = 1

        for file in glob.glob(os.path.join(folder_path, '*.nd2')):
            print("Processing file:", file)
            try:
                with ND2Reader(file) as images:
                    img = np.asarray(images[0])  # Assuming you want the first image
            
                h, w = img.shape
                entropy_filtered_image = entropy(img, disk(5))
                threshold = threshold_otsu(entropy_filtered_image)
                Scratch = entropy_filtered_image < threshold
            
                plt.subplot(3, 3, i)
                i += 1
                plt.imshow(Scratch, cmap='gray')  # Showing the Scratch
            
                area = np.sum(Scratch == 1) * 100.0 / (h * w)
                binary = entropy_filtered_image <= threshold
                scratch_area = np.sum(binary == 1)
                print("Scratch area=", scratch_area, "pix²")
            
                area_list.append({'Sr. No.': i, 'Name': f"{folder_name}_{os.path.basename(file)}", 'Scratch Area': scratch_area, 'Percentage': area})
        
            except Exception as e:
                print("Error processing file:", file)
                print("Error message:", str(e))
            
        for subfolder in os.listdir(folder_path):
            subfolder_path = os.path.join(folder_path, subfolder)
            if os.path.isdir(subfolder_path):
                area_list.extend(process_images_in_folder(subfolder_path, f"{folder_name}_{subfolder}"))

        return area_list

    # Specify the root folder
    root_folder = r"D:\New folder\Desktop\DATA RSL\SCRATCH ASSAY\DATA\SET 5 FBS 17-04-24\48 hrs"
    root_folder = root_folder.strip()  # Remove leading and trailing whitespaces

    # Call the function to start analyzing images
    result_area_list = process_images_in_folder(root_folder)

    # Create a DataFrame from area_list
    df = pd.DataFrame(result_area_list)

    # Specify the Excel file path
    excel_file_path = r"C:\Users\Admin\Desktop\48hrsanalysis_results.xlsx"

    # Export the DataFrame to Excel
    df.to_excel(excel_file_path, index=False)
    print(f"Data exported to {excel_file_path}")
    # At the end, prepare outputs
    try:
        excel_bytes = _to_excel_bytes(results_df)
    except Exception:
        excel_bytes = None
    try:
        chart_fig = plt.gcf()
    except Exception:
        chart_fig = None

    return results_df, excel_bytes, chart_fig
