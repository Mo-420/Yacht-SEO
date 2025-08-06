# Yacht SEO

Generate SEO-optimized descriptions for yachts using the Groq LLM.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)

## Quick start (bash)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Provide your API key
echo "GROQ_API_KEY=sk-..." > .env

# Run demo with the included sample file
python generate_descriptions.py --demo
```

Windows PowerShell:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
setx GROQ_API_KEY "sk-..."
python generate_descriptions.py --demo
```

Swap `sample_yachts.csv` with your production `yachts.csv` when you’re ready.

---

### Environment variables

* `GROQ_API_KEY` – required. Your Groq API key.
* `GROQ_MODEL` (optional) – model slug to use. Defaults to `gpt-oss-120b`.
* `GROQ_API_BASE` (optional) – override the API base URL, e.g. for regional compliance.

You can set these in a `.env` file or directly in your shell.

---

### Command-line options

```
--input   Path to input CSV (default: yachts.csv)
--output  Path for output CSV (default: yacht_descriptions.csv)
--batch   Number of yachts per request (reserved for future batching)
--demo    Use the bundled sample_yachts.csv as input
```

---

### Project structure

```
.gitignore
.env              # your secrets (ignored by git)
requirements.txt   # dependencies
sample_yachts.csv  # example input
generate_descriptions.py  # main script
sheets.py          # future Google Sheets hook

---

## Deploy to Streamlit Cloud (zero-install for users)

1. Push this repo to GitHub (public or private).
2. Sign in at <https://streamlit.io> → **Deploy an app**.
3. Select the repo/branch and set **main file** to `app.py`.
4. Click **Deploy** – Streamlit Cloud builds the app automatically.

Within a couple of minutes you’ll get a public HTTPS link like:

```
https://yacht-seo-abc123.streamlit.app
```

Share that link; anyone can open it on their phone or desktop, paste their Groq API key, upload a CSV, and generate descriptions – no command line required.

Optional:

* Map a custom domain under *Settings → Custom Domains*.
* Adjust upload limits in `.streamlit/config.toml` (already set to 50 MB).
* Add the Streamlit badge above (update the link with your unique URL).

[//]: # (Happy sailing!)
