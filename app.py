import streamlit as st
import pandas as pd
import yaml
from io import BytesIO
from PIL import Image
import tifffile
import pims
import os
import matplotlib.pyplot as plt
from skimage import color
from scratch_analysis import run_analysis  # your existing analysis logic
import numpy as np

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
            st.success("Login successful. Please refresh the page to continue.")
            st.stop()
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")

def logout_ui():
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False}
        st.success("Logged out. Please refresh the page to continue.")
        st.stop()

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
        return pims.open(file)  # returns ND2 frames iterable
    else:
        raise ValueError(f"Unsupported image type: {ext}")

# ---------- Preprocess Files ----------
def preprocess_file(f):
    ext = os.path.splitext(getattr(f, 'name', f))[1].lower()
    
    if ext in [".csv", ".xlsx", ".zip"]:
        return f  # leave as-is

    img_data = read_image(f)
    frames = []

    # Multi-frame ND2 or TIFF
    if hasattr(img_data, '__iter__') and not isinstance(img_data, np.ndarray):
        for i, frame in enumerate(img_data):
            if frame.ndim == 3 and frame.shape[2] in [3,4]:
                frame = color.rgb2gray(frame)
            frames.append(np.array(frame))
    else:
        # Single frame image
        if isinstance(img_data, np.ndarray):
            frame = img_data
        else:
            frame = np.array(img_data.convert('L'))  # PIL to grayscale
        frames.append(frame)

    return frames

# ---------- Streamlit App ----------
st.set_page_config(page_title="Scratch Assay UI", layout="wide")
st.title("Scratch Assay Analysis — Streamlit")

config = load_config()
if "auth" not in st.session_state:
    st.session_state["auth"] = {"is_authenticated": False}

if not st.session_state["auth"]["is_authenticated"]:
    login_ui(config)
else:
    st.sidebar.success(f"Logged in as {st.session_state['auth']['username']}")
    logout_ui()

    st.markdown("""
    **Upload your files:** Drag & drop or click to select files.  
    Supported types: CSV, XLSX, ZIP, TIFF, JP2, ND2, JPG/JPEG.
    """)

    # ---------- File Uploader ----------
    uploaded = st.file_uploader(
        "Upload one or more files",
        type=["csv", "xlsx", "zip", "tif", "tiff", "jp2", "nd2", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Drag files here or click to browse"
    )

    # Optional parameters
    with st.expander("Options"):
        show_chart = st.checkbox("Show chart", value=True)
        show_table = st.checkbox("Show result table", value=True)

    # ---------- Run Analysis ----------
    if st.button("Run Analysis", type="primary"):
        if not uploaded:
            st.warning("Please upload at least one file.")
            st.stop()

        try:
            # Preprocess all files into consistent format
            files_for_analysis = []
            for f in uploaded:
                processed = preprocess_file(f)
                files_for_analysis.append({"name": getattr(f, 'name', 'Image'), "frames": processed})

            # Run user analysis
            results_df, excel_bytes, chart_fig = run_analysis(uploaded_files=files_for_analysis)

            # Store results in session_state for persistence
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

        # Download buttons
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
