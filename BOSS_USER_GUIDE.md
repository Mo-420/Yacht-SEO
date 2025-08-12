### Yacht‑SEO Generator — Executive Guide

#### What it is
Generate SEO‑optimized yacht descriptions via web UI or HTTPS API. Handles large batches (e.g., 5,000 yachts).

#### Public URL
- App: [Railway deployment](https://web-production-8a928.up.railway.app/)

#### Web UI (no command line)
1. Open the URL above.
2. Upload a file in any of these formats:
   - CSV
   - JSON (array of objects or NDJSON)
   - Excel (.xlsx)
3. Optional: toggle “Use async mode” for very large files (recommended for 5k+ rows).
4. Click “Generate Descriptions” to download the result CSV.

Sample file in repo: `genny.csv`.

#### API Endpoints (HTTPS)
- GET `/health` → service status
- POST `/generate` → accepts CSV/JSON/Excel upload; returns CSV
- POST `/generate-single` → accepts a single yacht JSON; returns `{ yacht, description }`
- POST `/generate-async` → starts a background job for large files; returns `{ job_id, status }`
- GET `/jobs/{job_id}` → get job status (`queued|processing|completed|failed`)
- GET `/jobs/{job_id}/result` → download CSV when job is `completed`

#### Health check
```bash
curl -s https://web-production-8a928.up.railway.app/health
```

#### Generate from CSV (download result)
```bash
curl -fS -X POST \
  -F file=@/absolute/path/to/your.csv \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

#### Generate from JSON (array or NDJSON)
```bash
# JSON array example (file: yachts.json)
curl -fS -X POST \
  -F file=@yachts.json \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

#### Generate from Excel (.xlsx)
```bash
curl -fS -X POST \
  -F file=@yachts.xlsx \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

#### Large batch (async) — recommended for 5k+ yachts
```bash
# Start job
curl -s -X POST -F file=@big_yachts.xlsx https://web-production-8a928.up.railway.app/generate-async
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
curl -fS -X POST https://web-production-8a928.up.railway.app/generate-single \
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

#### Notes
- HTTPS is enabled; no login required.
- For browser cross‑origin calls, CORS is not enabled; use server‑to‑server or the web UI.

#### Link reference
- App: [Railway deployment](https://web-production-8a928.up.railway.app/)


