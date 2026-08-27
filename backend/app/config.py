"""Loads settings from backend/.env once, at import time."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

CACHE_DIR = BACKEND_DIR / ".cache" / "pages"

# Model tiering per design doc §11: larger model for profiling/synthesis,
# smaller model for extraction/classification. Prices are USD per million
# tokens, used to estimate cost_cents on runs.
MODEL_PROFILER = "claude-opus-4-8"
MODEL_EXTRACTOR = "claude-haiku-4-5"
MODEL_PRICES = {  # (input $/MTok, output $/MTok)
    "claude-opus-4-8": (5.00, 25.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def estimate_cost_cents(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = MODEL_PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000 * 100
