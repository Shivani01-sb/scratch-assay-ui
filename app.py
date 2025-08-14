import pandas as pd
import numpy as np
from io import BytesIO
import matplotlib.pyplot as plt

# Optional: if using image processing
from skimage import io, filters, color

def run_analysis(uploaded_files):
    """
    uploaded_files: list of files or image iterables (from read_image)
    Returns: results_df, excel_bytes, chart_fig
    """

    all_results = []

    for f in uploaded_files:
        try:
            # Handle image iterables (ND2, multi-frame TIFF)
            if hasattr(f, '__iter__') and not isinstance(f, (bytes, bytearray)):
                for i, frame in enumerate(f):
                    # Convert to grayscale if needed
                    if frame.ndim == 3 and frame.shape[2] in [3, 4]:  # RGB/RGBA
                        frame = color.rgb2gray(frame)

                    # Simple analysis example: mean intensity
                    mean_val = np.mean(frame)
                    all_results.append({
                        "file": getattr(f, 'filename', f"Image_{i}"),
                        "frame": i + 1,
                        "mean_intensity": mean_val
                    })
            # Handle CSV / Excel
            elif isinstance(f, (bytes, bytearray)) or getattr(f, 'name', '').lower().endswith(('.csv', '.xlsx')):
                if getattr(f, 'name', '').lower().endswith('.csv'):
                    df = pd.read_csv(f)
                else:
                    df = pd.read_excel(f)
                # Example: sum of first numeric column
                numeric_cols = df.select_dtypes(include=np.number).columns
                sum_val = df[numeric_cols[0]].sum() if len(numeric_cols) > 0 else np.nan
                all_results.append({
                    "file": getattr(f, 'name', 'DataFile'),
                    "frame": np.nan,
                    "sum_first_numeric_col": sum_val
                })
            # Otherwise: skip unsupported
            else:
                print(f"Skipping unsupported file: {getattr(f, 'name', f)}")
        except Exception as e:
            print(f"Error processing file {getattr(f, 'name', f)}: {e}")

    # Convert to DataFrame
    results_df = pd.DataFrame(all_results)

    # Prepare Excel bytes
    excel_buffer = BytesIO()
    results_df.to_excel(excel_buffer, index=False)
    excel_bytes = excel_buffer.getvalue()

    # Optional chart
    chart_fig = plt.figure(figsize=(8,4))
    if 'mean_intensity' in results_df.columns:
        plt.plot(results_df['frame'], results_df['mean_intensity'], marker='o')
        plt.title("Mean Intensity per Frame")
        plt.xlabel("Frame")
        plt.ylabel("Mean Intensity")
        plt.tight_layout()
    else:
        chart_fig = None

    return results_df, excel_bytes, chart_fig
