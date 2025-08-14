import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt
from skimage import color

def run_analysis(uploaded_files):
    """
    uploaded_files: list of dicts or files processed in app.py
        Each item can be:
        - {"name": file_name, "frames": [np.ndarray, ...]} for images
        - file-like CSV/XLSX/ZIP for data files
    Returns: results_df, excel_bytes, chart_fig
    """

    all_results = []

    for f in uploaded_files:
        try:
            # Image files
            if isinstance(f, dict) and "frames" in f:
                file_name = f.get("name", "ImageFile")
                frames = f["frames"]
                for i, frame in enumerate(frames):
                    # Ensure grayscale
                    if frame.ndim == 3 and frame.shape[2] in [3, 4]:
                        frame = color.rgb2gray(frame)
                    mean_val = np.mean(frame)
                    all_results.append({
                        "file": file_name,
                        "frame": i + 1,
                        "mean_intensity": mean_val
                    })

            # CSV/XLSX files
            elif isinstance(f, (bytes, bytearray)) or getattr(f, 'name', '').lower().endswith(('.csv', '.xlsx')):
                file_name = getattr(f, 'name', 'DataFile')
                if file_name.lower().endswith('.csv'):
                    df = pd.read_csv(f)
                else:
                    df = pd.read_excel(f)
                numeric_cols = df.select_dtypes(include=np.number).columns
                sum_val = df[numeric_cols[0]].sum() if len(numeric_cols) > 0 else np.nan
                all_results.append({
                    "file": file_name,
                    "frame": np.nan,
                    "sum_first_numeric_col": sum_val
                })
            else:
                all_results.append({
                    "file": getattr(f, 'name', str(f)),
                    "frame": np.nan,
                    "mean_intensity": np.nan
                })

        except Exception as e:
            print(f"Error processing file {getattr(f, 'name', f)}: {e}")
            all_results.append({
                "file": getattr(f, 'name', str(f)),
                "frame": np.nan,
                "mean_intensity": np.nan
            })

    # Convert to DataFrame
    results_df = pd.DataFrame(all_results)

    # Prepare Excel bytes
    excel_buffer = BytesIO()
    results_df.to_excel(excel_buffer, index=False)
    excel_bytes = excel_buffer.getvalue()

    # Optional chart for image frames
    chart_fig = None
    image_results = results_df.dropna(subset=['frame', 'mean_intensity'])
    if not image_results.empty:
        chart_fig = plt.figure(figsize=(8, 4))
        for file_name, group in image_results.groupby('file'):
            plt.plot(group['frame'], group['mean_intensity'], marker='o', label=file_name)
        plt.title("Mean Intensity per Frame")
        plt.xlabel("Frame")
        plt.ylabel("Mean Intensity")
        plt.legend()
        plt.tight_layout()

    return results_df, excel_bytes, chart_fig
