#!/usr/bin/env python3
"""
Simple yacht description generator using Groq API.
Usage: python generate_descriptions.py input.csv output.csv
"""

import os
import sys
import csv
import argparse
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from retrying import retry
from tqdm import tqdm
from rich.console import Console
import pandas as pd

# Third‐party Groq client
from groq import Groq

console = Console()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()  # pull variables from .env if present

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    console.print("[bold red]❌ GROQ_API_KEY not found. Add it to your env or .env file.[/]")
    sys.exit(1)

MODEL_ID = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Allow runtime control of sampling temperature via env var
try:
    _TEMP = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
except ValueError:
    _TEMP = 0.7

TOKEN_PRICE_IN = 0.15 / 1_000_000  # USD per prompt token
TOKEN_PRICE_OUT = 0.75 / 1_000_000  # USD per completion token

# System prompt for the AI
SYSTEM_PROMPT = """You are a seasoned yacht charter copywriter with 15+ years of experience writing for luxury travel publications. You have personally sailed the Mediterranean and know these waters intimately.

Your writing style:
• Conversational, warm, and personal - like a friend sharing insider knowledge
• Varied sentence lengths and structures - mix short punchy sentences with flowing descriptions
• Use contractions naturally (you'll, we've, it's, that's)
• Include personal observations and local insights
• Avoid repetitive patterns or formulaic structures
• Write with genuine enthusiasm and passion for sailing
• Use natural transitions between ideas
• Include specific details that show real knowledge of the area

Tone: Confident but approachable, like a trusted travel advisor who's been there
Voice: First-person insights mixed with second-person engagement
Style: Natural, flowing, with personality - not corporate or robotic

Remember: You're writing for real people who want authentic experiences, not generic marketing copy."""

# User prompt template
USER_PROMPT_TEMPLATE = """Write a compelling yacht description for {name} that feels like it's written by someone who's actually sailed on her. 

Here's what I know about this yacht:
- Name: {name}
- Built by {builder} in {year}
- Model: {model}
- Length: {length}m
- Accommodates {guests} guests in {cabins} cabins
- Crew of {crew}
- Weekly rate: {price}
- Water toys: {watertoys}
- Based in {location}

Write naturally, as if you're telling a friend about this amazing yacht you've chartered. Include:
- What makes this yacht special and unique
- What the experience is like on board
- Where you'd sail and what you'd do
- Why someone should choose this yacht

Keep it conversational and authentic. Don't be overly promotional - just share genuine enthusiasm for the experience. Use natural language, varied sentence structures, and personal insights.

Aim for around 600-800 words. Write in a way that feels human and engaging, not like marketing copy."""

client = Groq(api_key=API_KEY)

# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------

def make_prompt(row: Dict[str, str]) -> str:
    """Create the prompt for a single yacht."""
    return USER_PROMPT_TEMPLATE.format(
        name=row.get('name', 'Unknown'),
        builder=row.get('builder', 'N/A'),
        model=row.get('model', 'N/A'),
        year=row.get('year', 'N/A'),
        length=row.get('length', 'N/A'),
        guests=row.get('guests', 'N/A'),
        cabins=row.get('cabins', 'N/A'),
        crew=row.get('crew', 'N/A'),
        price=row.get('price', 'N/A'),
        watertoys=row.get('watertoys', 'N/A'),
        location=row.get('location', 'N/A')
    )

@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
def generate(prompt: str) -> Tuple[str, int, int]:
    """Call the Groq API and return (text, prompt_tokens, completion_tokens)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    resp = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        max_tokens=1100,
        temperature=_TEMP,
    )
    
    usage = resp.usage
    text = resp.choices[0].message.content.strip()

    # Handle usage data
    if usage:
        if isinstance(usage, dict):
            prompt_tok = usage.get("prompt_tokens", 0)
            completion_tok = usage.get("completion_tokens", 0)
        else:  # object with attributes
            prompt_tok = getattr(usage, "prompt_tokens", 0)
            completion_tok = getattr(usage, "completion_tokens", 0)
    else:
        prompt_tok = completion_tok = 0

    return text, prompt_tok, completion_tok

def process_csv(input_csv: str, output_csv: str) -> None:
    """Process the input CSV and generate descriptions."""
    # Read input CSV
    with open(input_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    console.print(f"[bold green]Processing {len(rows)} yachts...[/]")
    
    total_prompt = total_completion = 0
    out_rows = []

    # Process each yacht
    for i, row in enumerate(tqdm(rows, desc="Generating descriptions")):
        try:
            prompt = make_prompt(row)
            description, prompt_tokens, completion_tokens = generate(prompt)
            
            # Add description to output row
            out_row = row.copy()
            out_row['description'] = description
            out_rows.append(out_row)
            
            total_prompt += prompt_tokens
            total_completion += completion_tokens
            
            console.print(f"[green]✓[/] {row.get('name', 'Unknown')} - {len(description)} chars")
            
        except Exception as e:
            console.print(f"[bold red]✗[/] Error processing {row.get('name', 'Unknown')}: {e}")
            # Add row with error message
            out_row = row.copy()
            out_row['description'] = f"ERROR: {str(e)}"
            out_rows.append(out_row)

    # Write output CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        if out_rows:
            writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
            writer.writeheader()
            writer.writerows(out_rows)

    # Print cost summary
    cost = (total_prompt * TOKEN_PRICE_IN) + (total_completion * TOKEN_PRICE_OUT)
    console.print(f"\n[bold green]✅ Done![/]")
    console.print(f"Total cost: ${cost:.4f}")
    console.print(f"Output saved to: {output_csv}")

def main():
    global MODEL_ID, _TEMP
    
    parser = argparse.ArgumentParser(description="Generate yacht descriptions using Groq API")
    parser.add_argument("input", help="Input CSV file with yacht data")
    parser.add_argument("output", help="Output CSV file with descriptions")
    parser.add_argument("--model", default=MODEL_ID, help=f"Groq model ID (default: {MODEL_ID})")
    parser.add_argument("--temperature", type=float, default=_TEMP, help=f"Temperature (default: {_TEMP})")
    
    args = parser.parse_args()
    
    # Update globals if specified
    if args.model != MODEL_ID:
        MODEL_ID = args.model
    if args.temperature != _TEMP:
        _TEMP = args.temperature
    
    if not os.path.exists(args.input):
        console.print(f"[bold red]❌ Input file not found: {args.input}[/]")
        sys.exit(1)
    
    process_csv(args.input, args.output)

if __name__ == "__main__":
    main()