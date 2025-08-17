#!/usr/bin/env python3
"""
Simple FastAPI web service for yacht description generation.
Usage: uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
import tempfile
import csv
import json
import uuid
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Any, Optional, Literal
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from starlette.background import BackgroundTasks
from groq import Groq
import generate_descriptions as gd
import pandas as pd

# Import our existing generation logic
from generate_descriptions import (
    process_csv,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    make_prompt,
)

app = FastAPI(
    title="Yacht-SEO Generator API",
    description="Generate high-quality yacht descriptions using AI",
    version="1.0.0"
)

# Fixed model ID: do not allow overrides from params or env for API endpoints
FIXED_MODEL_ID = "openai/gpt-oss-120b"
GENERAL_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, precise AI assistant. Follow instructions carefully."
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory job registry for async processing
app.state.jobs: Dict[str, Dict[str, Any]] = {}

class YachtData(BaseModel):
    name: str
    length: float
    year: int
    price: str
    cabins: int
    guests: int
    crew: int
    watertoys: str
    location: str
    model: str
    builder: str

class CustomYachtRequest(BaseModel):
    system_prompt: str
    yacht: YachtData
    # Optional generation parameters (JSON only)
    class GenerationParams(BaseModel):
        model: Optional[str] = None
        temperature: Optional[float] = None
        max_tokens: Optional[int] = None

    params: Optional[GenerationParams] = None
    passphrase: Optional[str] = None
    # Additional customization for the user message
    user_instructions: Optional[str] = None
    prompt_mode: Optional[Literal['append', 'prepend', 'replace']] = 'append'

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/api")
async def api_info():
    return {
        "message": "Yacht-SEO Generator API",
        "usage": "Upload a CSV file to /generate or send yacht data to /generate-single",
        "services": [
            {"id": "seo", "name": "SEO Descriptions", "endpoints": [
                "/services/seo/generate", "/services/seo/generate-async", "/services/seo/generate-with-prompt", "/services/seo/generate-single"
            ]},
            {"id": "general", "name": "General Generator", "endpoints": [
                "/services/general/generate"
            ]}
        ]
    }

def _rows_from_upload(content: bytes, filename: str) -> List[Dict[str, Any]]:
    name = filename.lower()
    if name.endswith('.csv'):
        text = content.decode('utf-8', errors='replace')
        reader = csv.DictReader(text.splitlines())
        return list(reader)
    if name.endswith('.json'):
        # Try array JSON first
        try:
            data = json.loads(content.decode('utf-8', errors='replace'))
            if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                return [dict(row) for row in data['data']]
            if isinstance(data, list):
                return [dict(row) for row in data]
        except json.JSONDecodeError:
            pass
        # Try NDJSON
        rows: List[Dict[str, Any]] = []
        for line in content.decode('utf-8', errors='replace').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except json.JSONDecodeError:
                continue
        if rows:
            return rows
        raise HTTPException(status_code=400, detail="Invalid JSON. Provide an array of objects or NDJSON")
    if name.endswith('.xlsx') or name.endswith('.xls'):
        try:
            df = pd.read_excel(BytesIO(content))
            return df.to_dict(orient='records')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")
    raise HTTPException(status_code=400, detail="Unsupported file type. Use .csv, .json, or .xlsx")


def _write_rows_to_csv(rows: List[Dict[str, Any]], path: str) -> None:
    if not rows:
        raise HTTPException(status_code=400, detail="No rows found in uploaded file")
    # Normalize fieldnames to expected order when present
    preferred = [
        'name','length','year','price','cabins','guests','crew',
        'watertoys','location','model','builder'
    ]
    # Include any extra fields at the end
    fieldnames = preferred + [k for k in rows[0].keys() if k not in preferred]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, '') for k in fieldnames})


def _require_passphrase(request: Request, provided_passphrase: Optional[str] = None) -> None:
    """Enforce a fixed passphrase: 'YachtGPT'.

    Looks for passphrase in order of precedence: explicit provided value, header, query string.
    Headers checked: X-Passphrase, X-API-Passphrase
    Query param checked: passphrase
    """
    expected = "YachtGPT"

    header_value = (
        request.headers.get("x-passphrase")
        or request.headers.get("x-api-passphrase")
    )
    query_value = request.query_params.get("passphrase")
    candidate = provided_passphrase or header_value or query_value
    if candidate != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing passphrase")


def _process_csv_with_system_prompt(
    input_csv: str,
    output_csv: str,
    system_prompt: str,
    model_override: Optional[str] = None,
    temperature_override: Optional[float] = None,
    max_tokens_override: Optional[int] = None,
    user_instructions: Optional[str] = None,
    prompt_mode: Optional[str] = 'append',
) -> None:
    """Process the input CSV and generate descriptions using a custom system prompt.

    Optional overrides for model/temperature/max_tokens can be provided.
    """
    if not system_prompt or not system_prompt.strip():
        raise HTTPException(status_code=400, detail="system_prompt must be a non-empty string")

    # Read input CSV
    with open(input_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in the uploaded file")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set")

    client = Groq(api_key=api_key)

    out_rows: List[Dict[str, Any]] = []
    for row in rows:
        # Resolve per-request params with overrides or env defaults
        model_id = FIXED_MODEL_ID
        try:
            temperature = (
                float(temperature_override)
                if isinstance(temperature_override, (int, float))
                else float(os.getenv("GROQ_TEMPERATURE", "0.7"))
            )
        except ValueError:
            temperature = 0.7
        max_tokens = (
            max_tokens_override if isinstance(max_tokens_override, int) and max_tokens_override > 0 else 1100
        )

        try:
            base_prompt = make_prompt(row)
            prompt: str
            if user_instructions and user_instructions.strip():
                mode = (prompt_mode or 'append').lower()
                if mode == 'replace':
                    prompt = user_instructions.strip()
                elif mode == 'prepend':
                    prompt = f"{user_instructions.strip()}\n\n{base_prompt}"
                else:  # append (default)
                    prompt = f"{base_prompt}\n\n{user_instructions.strip()}"
            else:
                prompt = base_prompt
            resp = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            description = resp.choices[0].message.content.strip()
        except Exception as e:
            description = f"ERROR: {str(e)}"

        out_row = row.copy()
        out_row["description"] = description
        out_rows.append(out_row)

    # Write output CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
        writer.writeheader()
        writer.writerows(out_rows)


# Routers for service grouping
seo_router = APIRouter(prefix="/services/seo", tags=["seo"])
general_router = APIRouter(prefix="/services/general", tags=["general"])


# Legacy SEO endpoints (kept for compatibility)
@app.post("/generate")
async def generate_from_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    passphrase: Optional[str] = Form(None),
):
    """Generate descriptions from uploaded file: CSV, JSON (array/NDJSON), or Excel."""
    _require_passphrase(request, passphrase)
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as input_file:
        input_file_path = input_file.name
    # Prepare input CSV path from various formats
    try:
        rows = _rows_from_upload(content, file.filename)
        _write_rows_to_csv(rows, input_file_path)
    except HTTPException:
        # If the file is already a CSV, fall back to writing raw bytes
        if file.filename.lower().endswith('.csv'):
            with open(input_file_path, 'wb') as f:
                f.write(content)
        else:
            os.unlink(input_file_path)
            raise

    output_file_path = input_file_path.replace(".csv", "_output.csv")

    try:
        process_csv(input_file_path, output_file_path)
        background_tasks.add_task(os.unlink, output_file_path)
        return FileResponse(
            output_file_path,
            media_type="text/csv",
            filename=f"yacht_descriptions_{os.path.basename(file.filename).rsplit('.',1)[0]}.csv",
            background=background_tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        try:
            os.unlink(input_file_path)
        except:
            pass


def _process_job(job_id: str, input_bytes: bytes, filename: str) -> None:
    job = app.state.jobs[job_id]
    job['status'] = 'processing'
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as input_file:
            input_csv = input_file.name
        rows = _rows_from_upload(input_bytes, filename)
        _write_rows_to_csv(rows, input_csv)
        output_csv = input_csv.replace('.csv', '_output.csv')
        job['input_csv'] = input_csv
        job['output_csv'] = output_csv
        process_csv(input_csv, output_csv)
        job['status'] = 'completed'
        job['finished_at'] = datetime.utcnow().isoformat()
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        job['finished_at'] = datetime.utcnow().isoformat()


@app.post("/generate-async")
async def generate_async(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    passphrase: Optional[str] = Form(None),
):
    """Start an async job for large files (CSV/JSON/Excel). Returns a job id to poll."""
    _require_passphrase(request, passphrase)
    content = await file.read()
    job_id = str(uuid.uuid4())
    app.state.jobs[job_id] = {
        'id': job_id,
        'filename': file.filename,
        'status': 'queued',
        'created_at': datetime.utcnow().isoformat(),
    }
    background_tasks.add_task(_process_job, job_id, content, file.filename)
    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    job = app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get('status') != 'completed':
        raise HTTPException(status_code=409, detail=f"Job not completed (status={job.get('status')})")
    path = job.get('output_csv')
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Result not available")
    return FileResponse(path, media_type="text/csv", filename=f"yacht_descriptions_{job.get('filename','results')}.csv")

@app.post("/generate-single")
async def generate_single_yacht(
    request: Request,
    yacht: YachtData,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    passphrase: Optional[str] = None,
):
    """Generate description for a single yacht (direct Groq call)."""
    _require_passphrase(request, passphrase)
    yacht_dict = yacht.dict()
    try:
        prompt = make_prompt(yacht_dict)
        # Prefer explicit model here to avoid environment/model issues
        model_id = FIXED_MODEL_ID
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens if isinstance(max_tokens, int) and max_tokens > 0 else 1100,
            temperature=(
                float(temperature)
                if isinstance(temperature, (int, float))
                else float(os.getenv("GROQ_TEMPERATURE", "0.7"))
            ),
        )
        description = resp.choices[0].message.content.strip()
        return {"yacht": yacht_dict, "description": description}
    except Exception as e:
        # Include the model in the error to aid debugging
        raise HTTPException(status_code=500, detail=f"Processing error ({type(e).__name__}): {str(e)}; model={FIXED_MODEL_ID}")


@app.post("/generate-single-custom")
async def generate_single_yacht_custom(request: Request, payload: CustomYachtRequest):
    """Generate description for a single yacht with a custom system prompt."""
    _require_passphrase(request, payload.passphrase)
    yacht_dict = payload.yacht.dict()
    system_prompt = payload.system_prompt
    if not system_prompt or not system_prompt.strip():
        raise HTTPException(status_code=400, detail="system_prompt must be a non-empty string")
    try:
        base_prompt = make_prompt(yacht_dict)
        if payload.user_instructions and payload.user_instructions.strip():
            mode = (payload.prompt_mode or 'append').lower()
            if mode == 'replace':
                prompt = payload.user_instructions.strip()
            elif mode == 'prepend':
                prompt = f"{payload.user_instructions.strip()}\n\n{base_prompt}"
            else:
                prompt = f"{base_prompt}\n\n{payload.user_instructions.strip()}"
        else:
            prompt = base_prompt
        model_id = FIXED_MODEL_ID
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=(
                payload.params.max_tokens
                if payload.params and isinstance(payload.params.max_tokens, int) and payload.params.max_tokens > 0
                else 1100
            ),
            temperature=(
                payload.params.temperature
                if payload.params and isinstance(payload.params.temperature, (int, float))
                else float(os.getenv("GROQ_TEMPERATURE", "0.7"))
            ),
        )
        description = resp.choices[0].message.content.strip()
        return {"yacht": yacht_dict, "description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error ({type(e).__name__}): {str(e)}; model={FIXED_MODEL_ID}")


@app.post("/generate-with-prompt")
async def generate_from_upload_with_prompt(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    system_prompt: str = Form(...),
    model: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    max_tokens: Optional[int] = Form(None),
    passphrase: Optional[str] = Form(None),
    user_instructions: Optional[str] = Form(None),
    prompt_mode: Optional[str] = Form('append'),
):
    """Generate descriptions from an uploaded file using a custom system prompt."""
    _require_passphrase(request, passphrase)
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as input_file:
        input_file_path = input_file.name
    # Prepare input CSV path from various formats
    try:
        rows = _rows_from_upload(content, file.filename)
        _write_rows_to_csv(rows, input_file_path)
    except HTTPException:
        if file.filename.lower().endswith('.csv'):
            with open(input_file_path, 'wb') as f:
                f.write(content)
        else:
            os.unlink(input_file_path)
            raise

    output_file_path = input_file_path.replace(".csv", "_output.csv")

    try:
        _process_csv_with_system_prompt(
            input_file_path,
            output_file_path,
            system_prompt,
            model_override=model,
            temperature_override=temperature,
            max_tokens_override=max_tokens,
            user_instructions=user_instructions,
            prompt_mode=prompt_mode,
        )
        background_tasks.add_task(os.unlink, output_file_path)
        return FileResponse(
            output_file_path,
            media_type="text/csv",
            filename=f"yacht_descriptions_{os.path.basename(file.filename).rsplit('.',1)[0]}.csv",
            background=background_tasks
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        try:
            os.unlink(input_file_path)
        except:
            pass


# Service: SEO (mirrors legacy endpoints under /services/seo)
@seo_router.post("/generate")
async def seo_generate_from_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    passphrase: Optional[str] = Form(None),
):
    return await generate_from_upload(request, background_tasks, file, passphrase)


@seo_router.post("/generate-async")
async def seo_generate_async(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    passphrase: Optional[str] = Form(None),
):
    return await generate_async(request, background_tasks, file, passphrase)


@seo_router.post("/generate-single")
async def seo_generate_single(
    request: Request,
    yacht: YachtData,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    passphrase: Optional[str] = None,
):
    return await generate_single_yacht(request, yacht, model, temperature, max_tokens, passphrase)


@seo_router.post("/generate-with-prompt")
async def seo_generate_with_prompt(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    system_prompt: str = Form(...),
    model: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    max_tokens: Optional[int] = Form(None),
    passphrase: Optional[str] = Form(None),
    user_instructions: Optional[str] = Form(None),
    prompt_mode: Optional[str] = Form('append'),
):
    return await generate_from_upload_with_prompt(
        request,
        background_tasks,
        file,
        system_prompt,
        model,
        temperature,
        max_tokens,
        passphrase,
        user_instructions,
        prompt_mode,
    )


# Service: General-purpose generator
class GeneralRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    passphrase: Optional[str] = None


@general_router.post("/generate")
async def general_generate(request: Request, payload: GeneralRequest):
    _require_passphrase(request, payload.passphrase)
    system_prompt = (payload.system_prompt or GENERAL_DEFAULT_SYSTEM_PROMPT).strip()
    if not system_prompt:
        system_prompt = GENERAL_DEFAULT_SYSTEM_PROMPT
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=FIXED_MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.prompt},
            ],
            max_tokens=(payload.max_tokens if isinstance(payload.max_tokens, int) and payload.max_tokens > 0 else 1100),
            temperature=(payload.temperature if isinstance(payload.temperature, (int, float)) else float(os.getenv("GROQ_TEMPERATURE", "0.7"))),
        )
        content = resp.choices[0].message.content.strip()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error ({type(e).__name__}): {str(e)}; model={FIXED_MODEL_ID}")


# Register routers
app.include_router(seo_router)
app.include_router(general_router)


# Compatibility aliases for General service (in case clients call different paths)
@app.post("/general/generate")
async def general_generate_alias(request: Request, payload: GeneralRequest):
    return await general_generate(request, payload)


@app.post("/generate-general")
async def generate_general_legacy(request: Request, payload: GeneralRequest):
    return await general_generate(request, payload)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api_key_set": bool(os.getenv("GROQ_API_KEY"))}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
