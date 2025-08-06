# --- Standard libs ---
import os
import tempfile

# --- Third-party ---
import pandas as pd
import streamlit as st
from streamlit_lottie import st_lottie
import requests

# ------------------------------------------------------------
# Pre-load GROQ key (if provided via secrets) before downstream imports
# ------------------------------------------------------------

_PRELOAD_GROQ_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
if _PRELOAD_GROQ_KEY:
    os.environ["GROQ_API_KEY"] = _PRELOAD_GROQ_KEY

# Local modules (import AFTER env is set so they pick it up)
from generate_descriptions import run as generate

st.set_page_config(
    page_title="Yacht-SEO Generator",
    page_icon="🛥️",
    layout="wide",
    initial_sidebar_state="expanded",
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

DEFAULT_GROQ_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")

# Ask for key only if not already supplied via environment/secrets
if DEFAULT_GROQ_KEY:
    api_key = DEFAULT_GROQ_KEY  # use predefined key
else:
    api_key = st.sidebar.text_input("Groq API key", type="password")
batch_size = st.sidebar.number_input("Batch size", min_value=1, value=1, step=1, help="How many yachts to send per API request")
verbose = st.sidebar.checkbox("Verbose per-yacht cost log")
refine = st.sidebar.checkbox("Refine / proofread descriptions")

uploaded = st.file_uploader("Upload your yachts.csv", type="csv")

if st.button("Generate descriptions"):
    if not uploaded:
        st.error("Please upload a CSV file of yachts first.")
        st.stop()
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()

    # Persist uploaded file to a temp location for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_in:
        tmp_in.write(uploaded.getbuffer())
        tmp_in_path = tmp_in.name
    out_path = tmp_in_path.replace(".csv", "_descriptions.csv")

    # Pass key to underlying script via env var
    os.environ["GROQ_API_KEY"] = api_key

    with st.spinner("Generating yacht descriptions … this may take a minute …"):
        generate(tmp_in_path, out_path, batch_size, verbose, refine)

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