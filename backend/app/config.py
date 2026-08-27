"""Loads settings from backend/.env once, at import time."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

CACHE_DIR = BACKEND_DIR / ".cache" / "pages"
