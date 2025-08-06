import os
import sys
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
    sys.exit(1)

MODEL_ID = os.getenv("GROQ_MODEL", "gpt-oss-120b")
API_BASE = os.getenv("GROQ_API_BASE")  # optional custom endpoint

TOKEN_PRICE_IN = 0.15 / 1_000_000  # USD per prompt token
TOKEN_PRICE_OUT = 0.75 / 1_000_000  # USD per completion token

# Long-form SEO prompt base
PROMPT_BASE = (
    "Write a 700-word, SEO-optimised luxury-yacht description. "
    "Use keywords: luxury catamaran Greece, Sunreef 80 charter, Mediterranean yacht holidays, "
    "private yacht with water toys. "
    "Add <h2>/<h3> headings (Interiors, Accommodation, Watertoys, Destinations, Crew). "
    "Conclude with a 140-character meta description and a clear call-to-action. "
    "Keep strictly to the supplied data; do NOT invent features.\n\n"
)

client_kwargs = dict(api_key=API_KEY)
if API_BASE:
    client_kwargs["base_url"] = API_BASE
client = Groq(**client_kwargs)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_prompt(row: Dict[str, str]) -> str:
    """Craft the prompt for a single yacht record based on the global PROMPT_BASE."""
    details = (
        f"Name: {row.get('name', 'Unknown')}\n"
        f"Length: {row.get('length', 'N/A')} meters\n"
        f"Year: {row.get('year', 'N/A')}\n"
        f"Price: ${row.get('price', 'N/A')}\n"
    )
    return PROMPT_BASE + details


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000, stop_max_attempt_number=5)
def generate(prompt: str) -> Tuple[str, int, int]:
    """Call the Groq API and return (text, prompt_tokens, completion_tokens)."""
    resp = client.chat.completions.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1100,
        temperature=0.7,
    )
    usage = resp.usage  # type: ignore[attr-defined]
    text = resp.choices[0].message.content.strip()  # type: ignore[index]
    return text, usage["prompt_tokens"], usage["completion_tokens"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(input_csv: str, output_csv: str, batch_size: int, verbose: bool) -> None:
    with open(input_csv, newline="", encoding="utf-8") as f:
        rows: List[Dict[str, str]] = list(csv.DictReader(f))

    total_prompt = total_completion = 0
    out_rows: List[Dict[str, str]] = []

    for start in tqdm(range(0, len(rows), batch_size), desc="Yachts processed (batches)"):
        batch = rows[start : start + batch_size]

        # Build prompt for batch
        if batch_size == 1:
            prompt = make_prompt(batch[0])
        else:
            yacht_blocks = [make_prompt(r) for r in batch]
            prompt = (
                PROMPT_BASE
                + "Below are several yachts separated by '---'. For each yacht, "
                  "return its description separated by \n---\n in the same order.\n\n"
                + "\n---\n".join(yacht_blocks)
            )

        text, used_prompt, used_completion = generate(prompt)
        total_prompt += used_prompt
        total_completion += used_completion
        cost_batch = used_prompt * TOKEN_PRICE_IN + used_completion * TOKEN_PRICE_OUT

        # Split descriptions (or replicate if batch_size == 1)
        descriptions = [text] if batch_size == 1 else [d.strip() for d in text.split("\n---\n") if d.strip()]
        if len(descriptions) != len(batch):
            console.print("[bold yellow]⚠️ Could not split descriptions as expected; writing raw output.[/]")
            descriptions = [text] * len(batch)

        for row, desc in zip(batch, descriptions):
            row["seo_description"] = desc
            if verbose:
                cost_each = cost_batch / len(batch)
                console.log(f"${cost_each:.4f} for {row.get('name', 'Unknown')}")

        out_rows.extend(batch)

    # Write output file
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
        writer.writeheader()
        writer.writerows(out_rows)

    cost_total = total_prompt * TOKEN_PRICE_IN + total_completion * TOKEN_PRICE_OUT
    console.print(
        f"[bold green]✅ Finished.[/] Prompt tokens: {total_prompt:,}, "
        f"Completion tokens: {total_completion:,}, Cost ≈ ${cost_total:,.2f}"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SEO descriptions for yachts using Groq")
    p.add_argument("--input", default="yachts.csv", help="Input CSV file path")
    p.add_argument("--output", default="yacht_descriptions.csv", help="Output CSV path")
    p.add_argument("--batch", type=int, default=1, help="Number of yachts per API request")
    p.add_argument("--demo", action="store_true", help="Use sample_yachts.csv as input")
    p.add_argument("--verbose", action="store_true", help="Print per-yacht cost during processing")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    input_file = "sample_yachts.csv" if args.demo else args.input
    if not os.path.exists(input_file):
        console.print(f"[bold red]❌ Input CSV not found: {input_file}[/]")
        sys.exit(1)

    run(input_file, args.output, max(1, args.batch), args.verbose)