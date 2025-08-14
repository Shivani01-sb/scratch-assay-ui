import streamlit as st
import pandas as pd
import yaml
from io import BytesIO
import matplotlib.pyplot as plt
from scratch_analysis import run_analysis

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
            st.experimental_rerun()  # <-- force reload to show uploader
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")

def logout_ui():
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False}
        st.experimental_rerun()  # <-- force reload after logout

# ---------- App ----------
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
    **Upload your files:** You can drag & drop or click to select CSV, Excel, or ZIP files.
    Your existing processing logic should live in `scratch_analysis.py::run_analysis`.
    """)

    # ---------- File Uploader ----------
    uploaded = st.file_uploader(
        "Upload one or more files (CSV, XLSX, ZIP)",
        type=["csv", "xlsx", "zip"],
        accept_multiple_files=True,
        help="Drag files here or click to browse"
    )

    # Optional parameters / switches
    with st.expander("Options"):
        show_chart = st.checkbox("Show chart", value=True)
        show_table = st.checkbox("Show result table", value=True)

    # ---------- Run Analysis ----------
    if st.button("Run Analysis", type="primary"):
        if not uploaded:
            st.warning("Please upload at least one file.")
            st.stop()

        try:
            results_df, excel_bytes, chart_fig = run_analysis(uploaded_files=uploaded)

            if show_table and isinstance(results_df, pd.DataFrame):
                st.subheader("Results")
                st.dataframe(results_df, use_container_width=True)

            if show_chart and chart_fig is not None:
                st.subheader("Chart")
                st.pyplot(chart_fig, clear_figure=False)

            # Downloads
            if isinstance(excel_bytes, (bytes, bytearray)):
                st.download_button(
                    "Download Excel Results",
                    data=excel_bytes,
                    file_name="results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            if chart_fig is not None:
                buf = BytesIO()
                chart_fig.savefig(buf, format="png", bbox_inches="tight")
                st.download_button(
                    "Download Chart (PNG)",
                    data=buf.getvalue(),
                    file_name="chart.png",
                    mime="image/png",
                )

            st.success("Analysis completed.")
        except Exception as e:
            st.error(f"Error during analysis: {e}")
            st.exception(e)
