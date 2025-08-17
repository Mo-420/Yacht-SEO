### Yacht‑SEO Generator — Final Boss Guide

#### Access
- App URL: [Hosted App](https://web-production-8a928.up.railway.app/)
- Passphrase (required): `YachtGPT`
  - Provide via header `X-Passphrase: YachtGPT`, query `?passphrase=YachtGPT`, form field `passphrase=YachtGPT`, or JSON field `"passphrase":"YachtGPT"` (single-custom only)

#### Model
- Fixed model for API: `openai/gpt-oss-120b` (cannot be changed)
- Tunables supported: `temperature`, `max_tokens`

#### Web UI (simple)
1. Open the app URL.
2. Enter passphrase `YachtGPT`.
3. Choose a Service:
   - SEO Descriptions: upload CSV/JSON/Excel (async available for large files) and download CSV with descriptions.
   - General Generator: enter a freeform prompt (and optional system prompt) and get a text response.
4. Click Generate.

#### API Endpoints
- GET `/health` → health status
- Services
  - SEO (`/services/seo/...`)
    - POST `/services/seo/generate` → upload CSV/JSON/Excel; returns CSV
    - POST `/services/seo/generate-async` → starts background job; returns `{ job_id }`
    - GET `/jobs/{job_id}` → job status
    - GET `/jobs/{job_id}/result` → download CSV
    - POST `/services/seo/generate-with-prompt` → upload + custom `system_prompt`; supports `temperature`, `max_tokens`, `user_instructions`, `prompt_mode`
    - POST `/services/seo/generate-single` and legacy `/generate-single-custom`
  - General (`/services/general/...`)
    - POST `/services/general/generate` → JSON `{ prompt, system_prompt?, temperature?, max_tokens?, passphrase }`; returns `{ content }`

- Legacy (still available for compatibility)
  - POST `/generate`, `/generate-async`, `/generate-with-prompt`, `/generate-single`, `/generate-single-custom`

#### Quick Examples
- Health
```bash
curl -s https://web-production-8a928.up.railway.app/health
```

- Generate from CSV
```bash
curl -fS -X POST \
  -F file=@yachts.csv \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate \
  -o yacht_descriptions.csv
```

- Generate (Async)
```bash
curl -s -X POST \
  -F file=@big_yachts.xlsx \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate-async
```

- Single yacht
```bash
curl -fS -X POST 'https://web-production-8a928.up.railway.app/generate-single?passphrase=YachtGPT' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "GENNY", "length": 23.87, "year": 2021, "price": "€58,000 – €70,000",
    "cabins": 5, "guests": 10, "crew": 6,
    "watertoys": "Jacuzzi; Jet-ski; Seabob; SUP",
    "location": "Greece", "model": "Sunreef 80", "builder": "Sunreef Yachts"
  }'
```

- Single yacht with custom system prompt
```bash
curl -fS -X POST https://web-production-8a928.up.railway.app/generate-single-custom \
  -H 'Content-Type: application/json' \
  -d '{
    "passphrase": "YachtGPT",
    "system_prompt": "Write as a luxury travel editor...",
    "yacht": {
      "name": "GENNY", "length": 23.87, "year": 2021, "price": "€58,000 – €70,000",
      "cabins": 5, "guests": 10, "crew": 6, "watertoys": "Jacuzzi; Jet-ski; Seabob; SUP",
      "location": "Greece", "model": "Sunreef 80", "builder": "Sunreef Yachts"
    },
    "params": { "temperature": 0.6, "max_tokens": 1200 },
    "user_instructions": "Return strict JSON with keys: title, intro, features[], itinerary, meta.",
    "prompt_mode": "append"
  }'
```

- Bulk upload with custom system prompt
```bash
curl -fS -X POST \
  -F file=@yachts.csv \
  -F system_prompt='Write as a seasoned broker...' \
  -F user_instructions='Keep to 300-400 words; include 3 H2 headings.' \
  -F prompt_mode='append' \
  -F temperature=0.6 \
  -F max_tokens=1100 \
  -F passphrase=YachtGPT \
  https://web-production-8a928.up.railway.app/generate-with-prompt \
  -o yacht_descriptions.csv
```

#### General generator (freeform)
```bash
curl -fS -X POST https://web-production-8a928.up.railway.app/services/general/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Write a 2-paragraph teaser about a Mediterranean sailing vacation.",
    "system_prompt": "You are a concise, creative copywriter.",
    "temperature": 0.6,
    "max_tokens": 400,
    "passphrase": "YachtGPT"
  }'
```

#### Requirements
- Environment: `GROQ_API_KEY` must be set on the server.

#### Notes
- API model is fixed to `openai/gpt-oss-120b` for consistency and quality.

