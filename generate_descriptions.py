import os
import csv
import argparse
from typing import List, Dict, Tuple

from dotenv import load_dotenv
from retrying import retry
from tqdm import tqdm
from rich.console import Console

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
    exit(1)

MODEL_ID = os.getenv("GROQ_MODEL", "gpt-oss-120b")
API_BASE = os.getenv("GROQ_API_BASE")  # optional custom endpoint

TOKEN_PRICE_IN = 0.15 / 1_000_000  # USD per prompt token
TOKEN_PRICE_OUT = 0.75 / 1_000_000  # USD per completion token

client = Groq(api_key=API_KEY, base_url=API_BASE) if API_BASE else Groq(api_key=API_KEY)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_prompt(row: Dict[str, str]) -> str:
    """Craft the prompt for a single yacht record."""
    # Simple template — adjust fields as needed
    return (
        "Generate an engaging SEO description for the following yacht. "
        "Limit to ~120 words.\n\n"
        f"Name: {row.get('name', 'Unknown')}\n"
        f"Length: {row.get('length', 'N/A')} meters\n"
        f"Year: {row.get('year', 'N/A')}\n"
        f"Price: ${row.get('price', 'N/A')}\n"
    )


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
def generate(prompt: str) -> Tuple[str, int, int]:
    """Call the Groq API and return (text, prompt_tokens, completion_tokens)."""
    resp = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7,
    )
    usage = resp.usage  # type: ignore[attr-defined]
    text = resp.choices[0].message.content.strip()  # type: ignore[index]
    return text, usage["prompt_tokens"], usage["completion_tokens"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(input_csv: str, output_csv: str, batch_size: int) -> None:
    rows: List[Dict[str, str]] = []
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows.extend(reader)

    total_prompt = total_completion = 0
    out_rows: List[Dict[str, str]] = []

    for row in tqdm(rows, desc="Yachts processed"):
        prompt = make_prompt(row)
        text, used_prompt, used_completion = generate(prompt)
        total_prompt += used_prompt
        total_completion += used_completion
        row["seo_description"] = text
        out_rows.append(row)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
        writer.writeheader()
        writer.writerows(out_rows)

    cost = total_prompt * TOKEN_PRICE_IN + total_completion * TOKEN_PRICE_OUT
    console.print(
        f"[bold green]✅ Finished.[/] Prompt tokens: {total_prompt:,}, "
        f"Completion tokens: {total_completion:,}, Cost ≈ ${cost:,.2f}"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SEO descriptions for yachts using Groq")
    p.add_argument("--input", default="yachts.csv", help="Input CSV file path")
    p.add_argument("--output", default="yacht_descriptions.csv", help="Output CSV path")
    p.add_argument("--batch", type=int, default=1, help="Number of yachts per request (future use)")
    p.add_argument("--demo", action="store_true", help="Use sample_yachts.csv as input")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    input_file = "sample_yachts.csv" if args.demo else args.input
    if not os.path.exists(input_file):
        console.print(f"[bold red]❌ Input CSV not found: {input_file}[/]")
        exit(1)

    run(input_file, args.output, args.batch)