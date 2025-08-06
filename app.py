import os
import tempfile
import pandas as pd
import streamlit as st
from streamlit_lottie import st_lottie
import requests

from generate_descriptions import run as generate

st.set_page_config(
    page_title="Yacht-SEO Generator",
    page_icon="🛥️",
    layout="wide",
    initial_sidebar_state="expanded",
    theme=dict(
        primaryColor="#14f1ff",
        backgroundColor="#0e1117",
        secondaryBackgroundColor="#1c1f26",
        textColor="#e8e8e8",
        font="Fira Code",
    ),
)

# --------- Custom CSS for futuristic look ---------
st.markdown(
    """
    <style>
    /* Glass card */
    .glass {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }
    /* Neon download button */
    .stDownloadButton>button {
        color:#0e1117 !important;
        background:#14f1ff !important;
        border:none;
        border-radius:50px;
        padding:0.6rem 1.4rem;
        box-shadow:0 0 10px #14f1ff;
        transition: all 0.3s ease-in-out;
    }
    .stDownloadButton>button:hover {
        background:#1bffff !important;
        box-shadow:0 0 20px #1bffff;
        transform: translateY(-2px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("✨ AI-Powered Luxury-Yacht Copywriter")

# Lottie animation header

def load_lottie(url: str):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None

lottie_json = load_lottie("https://assets9.lottiefiles.com/packages/lf20_q5pk6p1k.json")
if lottie_json:
    st_lottie(lottie_json, speed=1, height=180, key="header_anim")

st.markdown("Upload a CSV of yachts, tweak settings on the left, and watch the neon magic unfold.")

api_key = st.sidebar.text_input("Groq API key", type="password")
batch_size = st.sidebar.number_input("Batch size", min_value=1, value=1, step=1, help="How many yachts to send per API request")
verbose = st.sidebar.checkbox("Verbose per-yacht cost log")
refine = st.sidebar.checkbox("Refine / proofread descriptions")
use_sheet = st.sidebar.checkbox("Use Google Sheet (bypass CSV upload)")
sheet_tab = st.sidebar.text_input("Sheet tab name", value="Sheet1") if use_sheet else "Sheet1"

if not use_sheet:
    uploaded = st.file_uploader("Upload your yachts.csv", type="csv")
else:
    uploaded = None

if st.button("Generate descriptions"):
    if not use_sheet and not uploaded:
        st.error("Please upload a CSV file of yachts first or enable 'Use Google Sheet'.")
        st.stop()
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()

    if not use_sheet:
        # Persist uploaded file to a temp location for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_in:
            tmp_in.write(uploaded.getbuffer())
            tmp_in_path = tmp_in.name
        out_path = tmp_in_path.replace(".csv", "_descriptions.csv")
    else:
        out_path = tempfile.NamedTemporaryFile(delete=False, suffix="_descriptions.csv").name

    # Pass key to underlying script via env var
    os.environ["GROQ_API_KEY"] = api_key

    with st.spinner("Generating yacht descriptions … this may take a minute …"):
        if use_sheet:
            # When using sheet, provide dummy file path for input_csv
            generate("sheet.csv", out_path, batch_size, verbose, refine, use_sheet=True, sheet_tab=sheet_tab)
        else:
            generate(tmp_in_path, out_path, batch_size, verbose, refine, use_sheet=False)

    # Preview results in a friendly table
    df = pd.read_csv(out_path)
    st.subheader("🔍 Preview of generated descriptions")
    for _, row in df.iterrows():
        with st.expander(f"🛥️ {row.get('name', 'Yacht')}"):
            html = row.get("seo_description_refined") if refine else row.get("seo_description")
            st.markdown(f"<div class='glass'>{html}</div>", unsafe_allow_html=True)
            st.code(html, language="html")

    # Offer download
    with open(out_path, "rb") as f:
        st.success("Done! Click below to download your new CSV.")
        fname = "yacht_descriptions_refined.csv" if refine else "yacht_descriptions.csv"
        st.download_button("📥 Download result CSV", f, file_name=fname, mime="text/csv")