import streamlit as st
from io import BytesIO
import tempfile
import os
from scratch_analysis import run_analysis

st.set_page_config(page_title="Scratch Assay UI", layout="wide")
st.title("Scratch Assay Analysis — Streamlit")

# ---------- File Uploader ----------
uploaded = st.file_uploader(
    "Upload your files (CSV, XLSX, ZIP, ND2, TIFF, JP2, JPG)",
    type=["csv","xlsx","zip","nd2","tif","tiff","jp2","jpg","jpeg"],
    accept_multiple_files=True
)

# Optional parameters
with st.expander("Options"):
    show_chart = st.checkbox("Show chart", value=True)
    show_table = st.checkbox("Show result table", value=True)

if st.button("Run Analysis"):
    if not uploaded:
        st.warning("Please upload at least one file.")
        st.stop()

    try:
        # Streamlit uploaded files are BytesIO — save ND2/TIFF to temp files
        files_for_analysis = []
        for f in uploaded:
            ext = os.path.splitext(f.name)[1].lower()
            if ext in [".nd2", ".tif", ".tiff"]:
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp_file.write(f.read())
                tmp_file.flush()
                tmp_file.seek(0)
                tmp_file.name = f.name  # Keep original name for results
                files_for_analysis.append(tmp_file)
            else:
                # CSV/XLSX/other files can be passed directly
                files_for_analysis.append(f)

        # Run the analysis
        results_df, excel_bytes, chart_fig = run_analysis(files_for_analysis)

        # ---------- Display Results ----------
        if show_table:
            st.subheader("Results")
            st.dataframe(results_df, use_container_width=True)

        if show_chart and chart_fig is not None:
            st.subheader("Chart")
            st.pyplot(chart_fig, clear_figure=False)

        # Download button
        st.download_button(
            "Download Excel Results",
            data=excel_bytes,
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.success("Analysis completed successfully!")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        st.exception(e)
