
# Scratch Assay Streamlit UI

One-platform pipeline: go from an existing Python script to a cloud-hosted, login-enabled UI using **Streamlit**.

## Quickstart

1. **Clone** this repo and open it in your IDE.
2. Put your processing logic in `scratch_analysis.py::run_analysis`.
3. Update credentials in `config.yaml` (change the `salt`, `cookie_key`, and password hash).
4. Run locally:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
5. **Deploy on Streamlit Community Cloud**:
   - Push this repo to GitHub.
   - Go to streamlit.io → Deploy app → select your repo and `app.py`.
   - Set **no secrets needed** (this example reads from `config.yaml`).  
     For better security, move secrets to **Streamlit Secrets** and read them via `st.secrets`.

## Replacing the Placeholder Logic

Edit `scratch_analysis.py` and implement your own `run_analysis` that returns:
- `results_df` (pandas DataFrame) for on-page table
- `excel_bytes` (bytes) for a downloadable Excel
- `chart_fig` (matplotlib Figure or `None`) for plotting

## Optional: Using Zip Uploads or Folders
This template is designed for file uploads in the cloud. If you need to process a folder on disk when running locally, accept a path and call `run_analysis(input_path=...)`.

## Security Notes
- This demo uses a simple salted SHA256 check loaded from `config.yaml`.
- Rotate and secure your `salt` and `cookie_key`.
- For production, prefer managed auth (OAuth via Streamlit) or `streamlit-authenticator` with hashed passwords and secure cookies.

## License
MIT
