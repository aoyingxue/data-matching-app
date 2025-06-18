# Data Matching App

A lightweight and interactive **Streamlit web app** for aligning raw tabular data with a reference mapping.

It helps you:
- Match messy or inconsistent fields (e.g. names, countries, regions) to a standard reference
- Manually fill in unmatched values in-browser
- Export cleaned data and an updated reference mapping for future reuse

## Key Features

- Upload raw data and reference files (`.csv`, `.xlsx`, `.json`)
- Match on one or more composite keys
- Apply calibrated values from reference
- Configure replacements or add new columns
- Manually map unmatched keys via UI
- Edit mapping table directly in browser
- Export cleaned data & updated mapping file

## Install & Run

User tutorial video is [here](tutorial-video-2025-06-17-15-06-29.webm).

```bash
pip install -r requirements.txt
streamlit run main.py