#!/usr/bin/env python3
"""
Simple FastAPI web service for yacht description generation.
Usage: uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
import tempfile
import csv
from typing import List, Dict
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from starlette.background import BackgroundTasks
from groq import Groq

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

@app.post("/generate")
async def generate_from_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Generate descriptions from uploaded CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as input_file:
        content = await file.read()
        input_file.write(content)
        input_file_path = input_file.name
    
    output_file_path = input_file_path.replace(".csv", "_output.csv")
    
    try:
        # Process the CSV
        process_csv(input_file_path, output_file_path)
        
        # Return the generated file and schedule cleanup after response is sent
        background_tasks.add_task(os.unlink, output_file_path)
        return FileResponse(
            output_file_path,
            media_type="text/csv",
            filename=f"yacht_descriptions_{file.filename}",
            background=background_tasks
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Clean up temp files (do not delete output here; it's scheduled in background)
        try:
            os.unlink(input_file_path)
        except:
            pass

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
