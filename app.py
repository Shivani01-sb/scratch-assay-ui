import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from io import BytesIO
import matplotlib.pyplot as plt
from skimage.filters.rank import entropy
from skimage.morphology import disk
from skimage.filters import threshold_otsu
from nd2reader import ND2Reader
from PIL import Image
import tifffile
import pims

# ---------- Auth Helpers ----------
def load_config():
    import yaml
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
            st.experimental_rerun()
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")

def logout_ui():
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False}
        st.experimental_rerun()

# ---------- Image Reader ----------
def read_image(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext in [".jpg", ".jpeg", ".png"]:
        return np.array(Image.open(file).convert("L"))
    elif ext in [".tif", ".tiff"]:
        return tifffile.imread(file)
    elif ext == ".jp2":
        return np.array(Image.open(file).convert("L"))
    elif ext == ".nd2":
        return ND2Reader(file)
    else:
        raise ValueError(f"Unsupported image type: {ext}")

# ---------- Scratch Assay Analysis ----------
def process_images_in_folder(folder_files, folder_name="Uploaded"):
    area_list = []
    i = 1
    for f in folder_files:
        try:
            if isinstance(f, ND2Reader) or hasattr(f, '__iter__'):
                # multi-frame ND2 or similar iterable
                frames = list(f)
                for idx, frame in enumerate(frames):
                    if frame.ndim == 3 and frame.shape[2] in [3,4]:
                        from skimage.color import rgb2gray
                        frame = rgb2gray(frame)
                    h, w = frame.shape
                    entropy_filtered = entropy(frame.astype(np.uint8), disk(5))
                    thresh = threshold_otsu(entropy_filtered)
                    binary = entropy_filtered <= thresh
                    scratch_area = np.sum(binary)
                    percentage = scratch_area * 100.0 / (h*w)
                    area_list.append({
                        "Sr. No.": i,
                        "Name": f"{folder_name}_{getattr(f,'filename', 'ND2_File')}_Frame{idx+1}",
                        "Scratch Area": scratch_area,
                        "Percentage": percentage
                    })
                    i += 1
            else:
                # single-frame image
                img = np.array(f)
                if img.ndim == 3 and img.shape[2] in [3,4]:
                    from skimage.color import rgb2gray
                    img = rgb2gray(img)
                h, w = img.shape
                entropy_filtered = entropy(img.astype(np.uint8), disk(5))
                thresh = threshold_otsu(entropy_filtered)
                binary = entropy_filtered <= thresh
                scratch_area = np.sum(binary)
                percentage = scratch_area * 100.0 / (h*w)
                area_list.append({
                    "Sr. No.": i,
                    "Name": f"{folder_name}_{getattr(f,'filename', 'Image_File')}",
                    "Scratch Area": scratch_area,
                    "Percentage": percentage
                })
                i += 1
        except Exception as e:
            st.warning(f"Error processing file {getattr(f,'filename', f)}: {e}")
    return area_list

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
    **Upload your image files:** Drag & drop or click to select.  
    Supported: ND2, TIFF, JP2, JPG/JPEG
    """)

    uploaded = st.file_uploader(
        "Upload one or more files",
        type=["nd2","tif","tiff","jp2","jpg","jpeg"],
        accept_multiple_files=True,
        help="Drag files here or click to browse"
    )

    if st.button("Run Analysis"):
        if not uploaded:
            st.warning("Please upload at least one file.")
            st.stop()
        try:
            # Read images
            files_for_analysis = []
            for f in uploaded:
                img = read_image(f)
                files_for_analysis.append(img)

            # Run analysis
            result_list = process_images_in_folder(files_for_analysis)
            results_df = pd.DataFrame(result_list)

            # Store results in session_state
            st.session_state["results_df"] = results_df

            # Excel export
            excel_buffer = BytesIO()
            results_df.to_excel(excel_buffer, index=False)
            st.session_state["excel_bytes"] = excel_buffer.getvalue()

            # Chart
            fig = plt.figure(figsize=(8,4))
            plt.bar(results_df['Sr. No.'], results_df['Scratch Area'])
            plt.title("Scratch Area per File/Frame")
            plt.xlabel("Sr. No.")
            plt.ylabel("Scratch Area")
            plt.tight_layout()
            st.session_state["chart_fig"] = fig

            st.success("Analysis completed and stored in session.")

        except Exception as e:
            st.error(f"Error during analysis: {e}")
            st.exception(e)

    # ---------- Display persistent results ----------
    if "results_df" in st.session_state:
        st.subheader("Results Table")
        st.dataframe(st.session_state["results_df"], use_container_width=True)

        st.download_button(
            "Download Excel Results",
            data=st.session_state["excel_bytes"],
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        if st.session_state.get("chart_fig") is not None:
            st.subheader("Scratch Area Chart")
            st.pyplot(st.session_state["chart_fig"], clear_figure=False)
            buf = BytesIO()
            st.session_state["chart_fig"].savefig(buf, format="png", bbox_inches="tight")
            st.download_button(
                "Download Chart (PNG)",
                data=buf.getvalue(),
                file_name="chart.png",
                mime="image/png",
            )
