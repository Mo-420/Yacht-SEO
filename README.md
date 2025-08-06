# Yacht SEO

Generate SEO-optimized descriptions for yachts using the Groq LLM.

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
```

[//]: # (Happy sailing!)
