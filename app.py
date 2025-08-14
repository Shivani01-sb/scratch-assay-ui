import streamlit as st
import pandas as pd
import yaml
from io import BytesIO
from PIL import Image
import tifffile
import pims
import os
import matplotlib.pyplot as plt
from scratch_analysis import process_images_in_folder  # your original working analysis

# ---------- Auth Helpers ----------
def load_config():
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

def verify_password(username, password, config):
    auth = config.get("auth", {})
    users = auth.get("users", [])
    salt = auth.get("salt", "")
    import hashlib
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    for u in users:
        if u.get("username") == username and u.get("password_sha256") == pw_hash:
            return True
    return False

def login_ui(config):
    st.sidebar.subheader("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Sign in"):
        if verify_password(username, password, config):
            st.session_state["auth"] = {"is_authenticated": True, "username": username}
            st.success("Login successful. You can now use the app.")
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")

def logout_ui():
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False}
        st.success("Logged out. Refresh page or re-login to continue.")

# ---------- Image Reader ----------
def read_image(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext in [".jpg", ".jpeg", ".png"]:
        return Image.open(file)
    elif ext in [".tif", ".tiff"]:
        return tifffile.imread(file)
    elif ext == ".jp2":
        return Image.open(file)  # PIL supports JP2 if OpenJPEG installed
    elif ext == ".nd2":
        return pims.open(file)  # ND2 frames iterable
    else:
        raise ValueError(f"Unsupported image type: {ext}")

# ---------- Streamlit App ----------
st.set_page_config(page_title="Scratch Assay UI", layout="wide")
st.title("Scratch Assay Analysis — Streamlit")

config = load_config()
if "auth" not in st.session_state:
    st.session_state["auth"] = {"is_authenticated": False}

# Login check
if not st.session_state["auth"]["is_authenticated"]:
    login_ui(config)
    st.stop()
else:
    st.sidebar.success(f"Logged in as {st.session_state['auth']['username']}")
    logout_ui()

# Instructions
st.markdown("""
**Upload your files:** Drag & drop or click to select files.  
Supported types: CSV, XLSX, ZIP, TIFF, JP2, ND2, JPG/JPEG.
""")

# File uploader
uploaded = st.file_uploader(
    "Upload one or more files",
    type=["csv", "xlsx", "zip", "tif", "tiff", "jp2", "nd2", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Drag files here or click to browse"
)

# Options
with st.expander("Options"):
    show_chart = st.checkbox("Show chart", value=True)
    show_table = st.checkbox("Show result table", value=True)

# ---------- Run Analysis ----------
if st.button("Run Analysis", type="primary"):
    if not uploaded:
        st.warning("Please upload at least one file.")
        st.stop()

    try:
        all_results = []
        chart_fig = plt.figure(figsize=(8,4))
        for f in uploaded:
            ext = os.path.splitext(f.name)[1].lower()
            if ext in [".csv", ".xlsx", ".zip"]:
                # delegate CSV/Excel/ZIP processing to your analysis
                # you can integrate CSV/Excel reading here if needed
                pass
            else:
                # Save uploaded image temporarily
                temp_dir = "temp_uploads"
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, f.name)
                with open(temp_path, "wb") as out_file:
                    out_file.write(f.read())

                # Run your original scratch assay analysis
                result_area_list = process_images_in_folder(temp_dir)
                all_results.extend(result_area_list)

        # Create DataFrame
        results_df = pd.DataFrame(all_results)

        # Excel bytes
        excel_buffer = BytesIO()
        results_df.to_excel(excel_buffer, index=False)
        excel_bytes = excel_buffer.getvalue()

        # Chart
        if show_chart and len(results_df) > 0:
            plt.bar(results_df['Sr. No.'], results_df['Scratch Area'])
            plt.title("Scratch Area per File")
            plt.xlabel("File Index")
            plt.ylabel("Scratch Area (pixels²)")
            plt.tight_layout()
        else:
            chart_fig = None

        # Save in session
        st.session_state["results_df"] = results_df
        st.session_state["excel_bytes"] = excel_bytes
        st.session_state["chart_fig"] = chart_fig

        st.success("Analysis completed and stored in session.")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        st.exception(e)

# ---------- Display persistent results ----------
if "results_df" in st.session_state:
    if show_table and isinstance(st.session_state["results_df"], pd.DataFrame):
        st.subheader("Results")
        st.dataframe(st.session_state["results_df"], use_container_width=True)

    if show_chart and st.session_state.get("chart_fig") is not None:
        st.subheader("Chart")
        st.pyplot(st.session_state["chart_fig"], clear_figure=False)

    if st.session_state.get("excel_bytes") is not None:
        st.download_button(
            "Download Excel Results",
            data=st.session_state["excel_bytes"],
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if st.session_state.get("chart_fig") is not None:
        buf = BytesIO()
        st.session_state["chart_fig"].savefig(buf, format="png", bbox_inches="tight")
        st.download_button(
            "Download Chart (PNG)",
            data=buf.getvalue(),
            file_name="chart.png",
            mime="image/png",
        )
