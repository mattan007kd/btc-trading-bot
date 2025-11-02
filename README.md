
# BTC Bot — Carry + Risk Dashboard (Cloud Ready)

A lightweight Streamlit app showcasing **Funding Carry (paper)** and **risk sizing (ATR)**.
Ready for **GitHub → Streamlit Community Cloud** or **Hugging Face Spaces**.

## Deploy on Streamlit Cloud
1. Push this repo to GitHub.
2. On streamlit.io/cloud → **New app** → select this repo.
3. App file: `streamlit_app.py` → **Deploy**.

## Deploy on Hugging Face Spaces
1. Create a Space (SDK: Streamlit).
2. Use the `hf_spaces/app.py` file as the main app (Spaces expects `app.py`).
3. Upload `requirements.txt` too.

## Local run
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Files
- `streamlit_app.py` — main Streamlit app (for Streamlit Cloud / local)
- `requirements.txt` — minimal deps
- `hf_spaces/app.py` — copy of the app named `app.py` for HF Spaces
- `.gitignore`, `LICENSE`, `README.md`
