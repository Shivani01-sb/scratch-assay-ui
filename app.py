import streamlit as st
import pandas as pd
import yaml
from io import BytesIO
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

# ---------- Initialize session state ----------
if "auth" not in st.session_state:
    st.session_state["auth"] = {"is_authenticated": False, "username": ""}

# ---------- App ----------
st.set_page_config(page_title="Scratch Assay UI", layout="wide")
st.title("Scratch Assay Analysis — Streamlit")

config = load_config()

# ---------- Sidebar: Login ----------
st.sidebar.subheader("Authentication")
if not st.session_state["auth"]["is_authenticated"]:
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Sign in"):
        if verify_password(username, password, config):
            st.session_state["auth"] = {"is_authenticated": True, "username": username}
        else:
            st.sidebar.error("Invalid credentials")
    st.sidebar.caption("Use credentials from config.yaml")

# ---------- Sidebar: Logout ----------
if st.session_state["auth"]["is_authenticated"]:
    st.sidebar.success(f"Logged in as {st.session_state['auth']['username']}")
    if st.sidebar.button("Sign out"):
        st.session_state["auth"] = {"is_authenticated": False, "username": ""}

# ---------- Main App: After Login ----------
if st.session_state["auth"]["is_authenticated"]:
    st.success("Login successful!")

    st.markdown("""
    **Upload your files:** You can drag & drop or click to select CSV, Excel, or ZIP files.
    """)

    # ---------- File Uploader ----------
    uploaded_files = st.file_uploader(
        "Upload one or more files (CSV, XLSX, ZIP)",
        type=["csv", "xlsx", "zip"],
        accept_multiple_files=True,
        key="uploader"
    )

    # ---------- Optional Parameters ----------
    with st.expander("Options"):
        show_chart = st.checkbox("Show chart", value=True)
        show_table = st.checkbox("Show result table", value=True)

    # ---------- Run Analysis ----------
    if st.button("Run Analysis"):
        if not uploaded_files:
            st.warning("Please upload at least one file before running analysis.")
        else:
            try:
                # Convert uploaded files to BytesIO for in-memory processing
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

                # ---------- Downloads ----------
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

                st.success("Analysis completed successfully!")

            except Exception as e:
                st.error(f"Error during analysis: {e}")
                st.exception(e)
