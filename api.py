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
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from starlette.background import BackgroundTasks
from groq import Groq
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

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/api")
async def api_info():
    return {
        "message": "Yacht-SEO Generator API",
        "usage": "Upload a CSV file to /generate or send yacht data to /generate-single"
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


@app.post("/generate")
async def generate_from_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Generate descriptions from uploaded file: CSV, JSON (array/NDJSON), or Excel."""
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
async def generate_async(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Start an async job for large files (CSV/JSON/Excel). Returns a job id to poll."""
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
async def generate_single_yacht(yacht: YachtData):
    """Generate description for a single yacht (direct Groq call)."""
    yacht_dict = yacht.dict()
    try:
        prompt = make_prompt(yacht_dict)
        # Prefer explicit model here to avoid environment/model issues
        model_id = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
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
            max_tokens=1100,
            temperature=float(os.getenv("GROQ_TEMPERATURE", "0.7")),
        )
        description = resp.choices[0].message.content.strip()
        return {"yacht": yacht_dict, "description": description}
    except Exception as e:
        # Include the model in the error to aid debugging
        raise HTTPException(status_code=500, detail=f"Processing error ({type(e).__name__}): {str(e)}; model={os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api_key_set": bool(os.getenv("GROQ_API_KEY"))}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
