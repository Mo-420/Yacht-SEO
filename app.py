import os
import tempfile
import streamlit as st

from generate_descriptions import run as generate

st.set_page_config(page_title="Yacht-SEO Generator", layout="centered")

st.title("🛥️ Yacht-SEO Description Builder")

st.markdown("Upload a CSV of yachts, enter your Groq API key, and get fully-formatted SEO descriptions back — no command line needed.")

api_key = st.sidebar.text_input("Groq API key", type="password")
batch_size = st.sidebar.number_input("Batch size", min_value=1, value=1, step=1, help="How many yachts to send per API request")
verbose = st.sidebar.checkbox("Verbose per-yacht cost log")

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
        generate(tmp_in_path, out_path, batch_size, verbose)

    with open(out_path, "rb") as f:
        st.success("Done! Click below to download your new CSV.")
        st.download_button("📥 Download yacht_descriptions.csv", f, file_name="yacht_descriptions.csv", mime="text/csv")