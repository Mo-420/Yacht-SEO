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

---

## Where do I get a Groq API key?

1. Sign up or log in at <https://console.groq.com>.
2. Go to **API Keys** → **Create Key**.  
3. Copy the key starting with `sk-` and paste it
   * into `.env` (local), **or**
   * into *Streamlit Cloud → Settings → Secrets* under the name `GROQ_API_KEY`.

The default model slug is already set to `gpt-oss-120b`; change `GROQ_MODEL` if Groq releases a newer model.

---

## Using Google Sheets instead of CSV

1. Enable the Google Sheets API and create a **service account** in Google Cloud.  
2. Download the JSON key and paste its entire contents (one line) into a secret
   called `GOOGLE_SHEET_CREDS` in Streamlit Cloud.
3. Share your target Sheet with the service-account email and grab the Sheet ID
   (string between `/d/` and `/edit` in the URL).  
4. Add another secret `SHEET_ID` with that value.  
5. In the app sidebar tick **“Use Google Sheet”** and specify the tab name if it’s
   not `Sheet1`.

When you click **Generate descriptions**, the app reads rows from the Sheet,
writes back the new `seo_description` (and optional
`seo_description_refined`) columns, and still offers a downloadable CSV.

[//]: # (Happy sailing!)
