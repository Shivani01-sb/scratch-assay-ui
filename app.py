import streamlit as st
import pandas as pd
import yaml
from io import BytesIO
import hashlib
import os
import sys

# ---------- Dynamic Import of scratch_analysis ----------
scratch_module_found = False
possible_paths = ['.', './src', './app']  # add more paths if needed

for path in possible_paths:
    sys.path.append(path)
    try:
        from scratch_analysis import run_analysis
        scratch_module_found = True
        break
    except ImportError:
        continue

if not scratch_module_found:
    st.error(
        "Error: scratch_analysis module not found.\n"
        "Make sure scratch_analysis.py is in the same folder or one of the subfolders.\n"
        f"Checked paths: {possible_paths}\n"
        f"Files in current folder: {os.listdir('.')}"
    )
    st.stop()

# ---------- Config & Auth Helpers ----------
def load_config():
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

def verify_password(username, password, config):
    auth = config.get("auth", {})
    users = auth.get("users", [])
    salt = auth.get("salt", "")
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return any(u.get("username") == username and u.get("password_sha256") == pw_hash for u in users)

# ---------- Session State Initialization ----------
if "auth" not in st.session_state:
    st.session_state["auth"] = {"is_authenticated": False, "username": ""}

# ---------- Page Config ----------
st.set_page_config(page_title="Scratch Assay UI", layout="wide")
st.title("Scratch Assay Analysis — Streamlit")

config = load_config()

# ---------- Sidebar: Authentication ----------
st.sidebar.subheader("Authentication")

if not st.session_state["auth"]["is_authenticated"]:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Sign in"):
        if verify_password(username, password, config):
            st.session_state["auth"] = {"is_authenticated": True, "username": username}
            st.sidebar.success(f"Logged in as {username}")
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")
else:
    st.sidebar.success(f"Logged in as {st.session_state['auth']['username']}")
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False, "username": ""}
        st.experimental_rerun()

# ---------- Main App: After Login ----------
if st.session_state["auth"]["is_authenticated"]:
    st.success("Login successful!")
    st.markdown("**Upload your files:** Drag & drop or click to select CSV, Excel, or ZIP files.")

    uploaded_files = st.file_uploader(
        "Upload one or more files",
        type=["csv", "xlsx", "zip"],
        accept_multiple_files=True,
        key="uploader"
    )

    with st.expander("Options"):
        show_chart = st.checkbox("Show chart", value=True)
        show_table = st.checkbox("Show result table", value=True)

    if st.button("Run Analysis"):
        if not uploaded_files:
            st.warning("Please upload at least one file before running analysis.")
        else:
            try:
                # Convert uploaded files to BytesIO
                uploaded_file_bytes = [BytesIO(f.getbuffer()) for f in uploaded_files]

                # Run analysis
                results_df, excel_bytes, chart_fig = run_analysis(uploaded_file_bytes)

                # Display Results Table
                if show_table and isinstance(results_df, pd.DataFrame):
                    st.subheader("Results")
                    st.dataframe(results_df, use_container_width=True)

                # Display Chart
                if show_chart and chart_fig is not None:
                    st.subheader("Chart")
                    st.pyplot(chart_fig, clear_figure=False)

                # Download Excel
                if isinstance(excel_bytes, (bytes, bytearray)):
                    st.download_button(
                        "Download Excel Results",
                        data=excel_bytes,
                        file_name="results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                # Download Chart
                if chart_fig is not None:
                    buf = BytesIO()
                    chart_fig.savefig(buf, format="png", bbox_inches="tight")
                    st.download_button(
                        "Download Chart (PNG)",
                        data=buf.getvalue(),
                        file_name="chart.png",
                        mime="image/png",
                    )

                st.success("Analysis completed successfully!")

            except Exception as e:
                st.error(f"Error during analysis: {e}")
                st.exception(e)
