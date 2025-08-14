import streamlit as st
import os
import tempfile
import yaml
from io import BytesIO
import pandas as pd
import matplotlib.pyplot as plt
from scratch_analysis import process_images_in_folder  # your original working analysis

# ------------------- Auth Helpers -------------------
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
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")

def logout_ui():
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False}
        st.experimental_rerun()

# ------------------- Streamlit App -------------------
st.set_page_config(page_title="Scratch Assay UI", layout="wide")
st.title("Scratch Assay Analysis — Streamlit")

config = load_config()
if "auth" not in st.session_state:
    st.session_state["auth"] = {"is_authenticated": False}

if not st.session_state["auth"]["is_authenticated"]:
    login_ui(config)
    st.stop()
else:
    st.sidebar.success(f"Logged in as {st.session_state['auth']['username']}")
    logout_ui()

st.markdown("""
**Upload your files:** Drag & drop or click to select files.  
Supported types: CSV, XLSX, ZIP, ND2, TIFF, JP2, JPG/JPEG.
""")

# ------------------- File Uploader -------------------
uploaded = st.file_uploader(
    "Upload one or more files",
    type=["csv","xlsx","zip","nd2","tif","tiff","jp2","jpg","jpeg"],
    accept_multiple_files=True,
    help="Drag files here or click to browse"
)

# Optional parameters
with st.expander("Options"):
    show_chart = st.checkbox("Show chart", value=True)
    show_table = st.checkbox("Show result table", value=True)

# ------------------- Run Analysis -------------------
if st.button("Run Analysis"):
    if not uploaded:
        st.warning("Please upload at least one file.")
        st.stop()

    try:
        # Create a temporary folder to save uploaded files
        temp_dir = tempfile.mkdtemp()

        for f in uploaded:
            file_path = os.path.join(temp_dir, f.name)
            with open(file_path, "wb") as out_file:
                out_file.write(f.read())

        # Call your original scratch assay analysis
        result_area_list = process_images_in_folder(temp_dir)
        results_df = pd.DataFrame(result_area_list)

        # Prepare Excel bytes for download
        excel_buffer = BytesIO()
        results_df.to_excel(excel_buffer, index=False)
        excel_bytes = excel_buffer.getvalue()

        # Store results in session_state for persistence
        st.session_state["results_df"] = results_df
        st.session_state["excel_bytes"] = excel_bytes

        # Generate optional chart
        if "Scratch Area" in results_df.columns:
            chart_fig, ax = plt.subplots(figsize=(10,5))
            ax.bar(results_df['Name'], results_df['Scratch Area'])
            ax.set_xlabel("File / Folder")
            ax.set_ylabel("Scratch Area (pixels)")
            ax.set_title("Scratch Area Analysis")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.session_state["chart_fig"] = chart_fig
        else:
            st.session_state["chart_fig"] = None

        st.success("Analysis completed successfully!")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        st.exception(e)

# ------------------- Display Persistent Results -------------------
if "results_df" in st.session_state:
    if show_table:
        st.subheader("Results Table")
        st.dataframe(st.session_state["results_df"], use_container_width=True)

    if show_chart and st.session_state.get("chart_fig") is not None:
        st.subheader("Chart")
        st.pyplot(st.session_state["chart_fig"], clear_figure=False)

    # Download buttons
    st.download_button(
        "Download Excel Results",
        data=st.session_state["excel_bytes"],
        file_name="results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.session_state.get("chart_fig") is not None:
        buf = BytesIO()
        st.session_state["chart_fig"].savefig(buf, format="png", bbox_inches="tight")
        st.download_button(
            "Download Chart (PNG)",
            data=buf.getvalue(),
            file_name="chart.png",
            mime="image/png"
        )

