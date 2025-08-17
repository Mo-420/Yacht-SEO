### Yacht‑SEO Generator — Executive Guide

#### What it is
Generate SEO‑optimized yacht descriptions via web UI or HTTPS API. Handles large batches (e.g., 5,000 yachts).

#### Public URL
- App: [Railway deployment](https://web-production-8a928.up.railway.app/)

#### Access Passphrase
- Required passphrase for all generation endpoints: `YachtGPT`
- Provide it via:
  - HTTP header: `X-Passphrase: YachtGPT` (or `X-API-Passphrase`)
  - Query string: `?passphrase=YachtGPT`
  - Form field (file uploads): `passphrase=YachtGPT`
  - JSON field (single-custom endpoint): `{"passphrase":"YachtGPT"}`

Sample file in repo: `genny.csv`.

#### Services and Endpoints (HTTPS)
- GET `/health` → service status
- SEO (`/services/seo/...`)
  - POST `/services/seo/generate` → accepts CSV/JSON/Excel upload; returns CSV
  - POST `/services/seo/generate-async` → starts a background job for large files; returns `{ job_id, status }`
  - GET `/jobs/{job_id}` → get job status (`queued|processing|completed|failed`)
  - GET `/jobs/{job_id}/result` → download CSV when job is `completed`
  - POST `/services/seo/generate-with-prompt` → upload with a custom system prompt and optional parameters; supports `user_instructions` and `prompt_mode` (`append|prepend|replace`)
  - POST `/services/seo/generate-single` and `/generate-single-custom` → single yacht generation
- General (`/services/general/...`)
  - POST `/services/general/generate` → JSON `{ prompt, system_prompt?, temperature?, max_tokens?, passphrase }`; returns `{ content }`

- Legacy endpoints remain available: `/generate`, `/generate-async`, `/generate-with-prompt`, `/generate-single`, `/generate-single-custom`

#### Health check
```bash
curl -s https://web-production-8a928.up.railway.app/health
```

#### Generate from CSV (download result)
```bash
curl -fS -X POST \
  -F file=@/absolute/path/to/your.csv \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

#### Generate from JSON (array or NDJSON)
```bash
# JSON array example (file: yachts.json)
curl -fS -X POST \
  -F file=@yachts.json \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

#### Generate from Excel (.xlsx)
```bash
curl -fS -X POST \
  -F file=@yachts.xlsx \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

#### Large batch (async) — recommended for 5k+ yachts
```bash
# Start job
curl -s -X POST -F file=@big_yachts.xlsx -F passphrase=YachtGPT https://web-production-8a928.up.railway.app/generate-async
# => {"job_id":"...","status":"queued"}

# Poll status until "completed"
curl -s https://web-production-8a928.up.railway.app/jobs/JOB_ID

# Download result when completed
curl -s \
  -o yacht_descriptions.csv \
  https://web-production-8a928.up.railway.app/jobs/JOB_ID/result
```

#### Single yacht example: GENNY
```bash
curl -fS -X POST 'https://web-production-8a928.up.railway.app/generate-single?passphrase=YachtGPT' \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GENNY",
    "length": 23.87,
    "year": 2021,
    "price": "€58,000 – €70,000",
    "cabins": 5,
    "guests": 10,
    "crew": 6,
    "watertoys": "Jacuzzi; Jet-ski; Seabob; SUP",
    "location": "Greece",
    "model": "Sunreef 80",
    "builder": "Sunreef Yachts"
  }'
```

#### Single yacht with custom system prompt
```bash
curl -fS -X POST https://web-production-8a928.up.railway.app/generate-single-custom \
  -H "Content-Type: application/json" \
  -d '{
    "passphrase": "YachtGPT",
    "system_prompt": "Write as a luxury travel editor...",
    "yacht": {
      "name": "GENNY",
      "length": 23.87,
      "year": 2021,
      "price": "€58,000 – €70,000",
      "cabins": 5,
      "guests": 10,
      "crew": 6,
      "watertoys": "Jacuzzi; Jet-ski; Seabob; SUP",
      "location": "Greece",
      "model": "Sunreef 80",
      "builder": "Sunreef Yachts"
    },
    "params": {
      "temperature": 0.6,
      "max_tokens": 1200
    }
  }'
```

#### Upload with custom system prompt (bulk)
```bash
curl -fS -X POST \
  -F file=@yachts.csv \
  -F system_prompt='Write as a seasoned broker...' \
  -F temperature=0.6 \
  -F max_tokens=1100 \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate-with-prompt \
  -o yacht_descriptions.csv
```

#### Notes
- HTTPS is enabled; no login required.
- For browser cross‑origin calls, CORS is not enabled; use server‑to‑server or the web UI.

#### Link reference
- App: [Railway deployment](https://web-production-8a928.up.railway.app/)


