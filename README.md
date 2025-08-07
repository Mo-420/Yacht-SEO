# Yacht-SEO Generator

Simple command-line tool to generate high-quality, SEO-optimized luxury yacht descriptions using the Groq API.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Groq API key:
```bash
export GROQ_API_KEY="your-api-key-here"
```

## Usage

Basic usage:
```bash
python generate_descriptions.py input.csv output.csv
```

With custom model and temperature:
```bash
python generate_descriptions.py input.csv output.csv --model "openai/gpt-oss-120b" --temperature 0.7
```

## Input CSV Format

Your CSV should have these columns:
- `name` - Yacht name
- `length` - Length in meters
- `year` - Build year
- `price` - Weekly charter rate
- `cabins` - Number of cabins
- `guests` - Guest capacity
- `crew` - Crew size
- `watertoys` - Available water toys
- `location` - Home port/location
- `model` - Yacht model
- `builder` - Yacht builder

## Example

```bash
# Test with the included sample
python generate_descriptions.py yachts.csv output.csv
```

The output CSV will contain all original columns plus a `description` column with the generated content.

## Features

- High-quality, SEO-optimized descriptions
- Professional yacht copywriting style
- HTML formatting with headings and structure
- Meta descriptions included
- Cost tracking and progress bars
- Error handling and retry logic
