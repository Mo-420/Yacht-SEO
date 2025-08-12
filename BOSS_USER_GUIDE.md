### Yacht‑SEO Generator — Boss Guide

#### What it is
Generate SEO‑optimized yacht descriptions via a web interface or HTTPS API.

#### Public URL
- App: [Railway deployment](https://web-production-8a928.up.railway.app/)

#### Web UI (no command line)
1. Open the URL above.
2. Upload a CSV with these columns: `name,length,year,price,cabins,guests,crew,watertoys,location,model,builder`.
3. Click “Generate Descriptions” to download the result CSV.

There is a ready CSV for GENNY in the repo: `genny.csv`.

#### API Endpoints (HTTPS)
- GET `/health` → service status
- POST `/generate` (multipart/form-data with `file=@your.csv`) → returns CSV
- POST `/generate-single` (application/json) → returns JSON `{ yacht, description }`

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

#### One‑click example: GENNY (single yacht)
Request (returns JSON with description):
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

Save only the description to an HTML file:
```bash
curl -s https://web-production-8a928.up.railway.app/generate-single \
  -H "Content-Type: application/json" \
  -d '{"name":"GENNY","length":23.87,"year":2021,"price":"€58,000 – €70,000","cabins":5,"guests":10,"crew":6,"watertoys":"Jacuzzi; Jet-ski; Seabob; SUP","location":"Greece","model":"Sunreef 80","builder":"Sunreef Yachts"}' \
  | python3 - << 'PY'
import sys, json
data = json.load(sys.stdin)
open('GENNY_description.html','w',encoding='utf-8').write(data.get('description',''))
print('Saved GENNY_description.html')
PY
```

#### CSV example: GENNY (upload + download)
The repo includes `genny.csv`. To generate a CSV result from it:
```bash
curl -fS -X POST \
  -F file=@genny.csv \
  https://web-production-8a928.up.railway.app/generate \
  -o GENNY_output.csv
```

#### Notes
- HTTPS is enabled; no credentials required right now.
- For browser calls from another origin, CORS is not configured; prefer server‑to‑server or use the web UI.

#### Link reference
- Public app: [Railway deployment](https://web-production-8a928.up.railway.app/)


