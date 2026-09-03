"""
Central configuration for Holidex.

Provides:
- Base URLs and timeouts for public holiday providers (Nager.Date API)
- Authentication keys and model identifiers for Gemini generative language services
- Project-relative filesystem paths for persistent local data (guides, comparisons, favourites)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file located at project root
load_dotenv()

# --- Nager.Date API Configuration ---
# Nager.Date v3 REST API endpoint used for country holiday schedules and available country listings.
NAGER_BASE_URL: str = "https://date.nager.at/api/v3"

# --- Google Gemini API Configuration ---
# API key obtained from Google AI Studio; loaded securely from the GEMINI_API_KEY environment variable.
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Gemini model identifier used for generating cultural holiday notes and contextual greetings.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# --- Local Storage Paths ---
# Base project directory resolved relative to this configuration file
PROJECT_DIR: Path = Path(__file__).resolve().parent

# Directory for storing application artifacts, cached data, and exported reports
DATA_DIR: str = str(PROJECT_DIR / "data")

# Path to the JSON file storing user-favourited country codes
FAVOURITES_FILE: str = os.path.join(DATA_DIR, "favourites.json")

# Directory where generated holiday guide Markdown summaries are exported
GUIDES_DIR: str = os.path.join(DATA_DIR, "guides")

# Directory where country-to-country holiday comparison reports are exported
COMPARISONS_DIR: str = os.path.join(DATA_DIR, "comparisons")