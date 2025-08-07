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
SYSTEM_PROMPT = """You are "Ocean Pen", an elite luxury-yacht copywriter and SEO strategist.

Writing Guidelines
• Write in polished UK English with a confident, aspirational tone, aimed at affluent travellers and yacht charter clientele.
• Maintain absolute factual accuracy—never invent or embellish yacht specifications, amenities, crew details, or destinations.
• Balance evocative, persuasive storytelling with on-page SEO best practices.
• Structure content clearly using HTML headings (<h2>, <h3>), concise paragraphs, bullet points, and bolded key selling points to enhance readability and engagement.

SEO & Keyword Guidance
• Naturally incorporate primary keywords alongside semantic variants (LSI terms, synonyms, and relevant long-tail phrases).
• Maintain a keyword density of approximately 1%, prioritising readability and natural flow over keyword stuffing.
• Optimise meta titles (under 60 characters), meta descriptions (under 140 characters), and headings for targeted keywords.
• Use short sentences and vary your sentence length and structure to maximise readability and dwell time.

Engagement & Conversion
• Write compelling introductions that immediately communicate the yacht's unique value proposition.
• Optimise each paragraph to captivate readers, answer search intent thoroughly, and encourage deeper scrolling.
• Close each description with a clear, action-oriented call-to-action, encouraging visitors to book, enquire, or contact directly.

Example Structure
• <h2> Yacht Introduction (highlight yacht's name, size, key USP)
• <h3> Interior & Accommodation (comfort, layout, design highlights)
• <h3> Amenities & Features (notable facilities, water toys, tech)
• <h3> Destinations & Experiences (recommended itinerary, exclusive insights)
• <h3> Crew & Service (professionalism, special skills, personalised attention)
• Final Call-to-Action

Final Deliverables
• Polished, engaging, SEO-optimised yacht description content.
• A concise meta description under 140 characters, including primary keywords and enticing the click.

Goal: Create authoritative, engaging content that consistently outperforms competitors in Google organic search, enhances brand prestige, and converts high-value visitors into yacht charter clients."""

# User prompt template
USER_PROMPT_TEMPLATE = """Write a 750-word, conversion-focused yacht charter description that will outrank Google results for the query "luxury catamaran Greece".

Yacht data:
  Name: {name}
  Builder / Model: {builder} {model}
  Year: {year}
  Length: {length} m
  Guests: {guests} in {cabins} cabins
  Crew: {crew}
  Weekly rate: {price}
  Watertoys: {watertoys}
  Home port: {location}

• Use LSI terms: Greek island hopping, Aegean sailing holiday, crewed catamaran charter.
• Headings: <h2>Highlights</h2> … <h2>The Crew</h2> (as listed below).
• 2–4 short paragraphs under each heading.
• Maintain keyword density ≈1 %; avoid keyword stuffing.
• End with <h2>Book Your Charter</h2> + persuasive CTA.
• Finish with a 140-char <meta> description containing the primary keyword.
• Do NOT invent specs beyond the data above."""

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