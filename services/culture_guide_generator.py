"""
CultureGuideGenerator: asks the Gemini API for the cultural/historical
meaning of a holiday plus a suggested greeting. Reads the API key from
config (which loads it from the GEMINI_API_KEY environment variable / .env).
"""
import json
import re
from typing import Any
import requests

from config import GEMINI_API_KEY, GEMINI_MODEL
from models.holiday import Holiday
from typing_defs import CultureResponse


class CultureGuideGenerator:
    """
    Generator service that queries Google's Gemini generative model to enrich
    public holidays with historical context and traditional greetings.

    Attributes:
        api_key: Secret API key for Google Generative Language API.
        model: Gemini model identifier (e.g. 'gemini-3.6-flash').
        endpoint: HTTP POST target for generateContent requests.
    """
    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL) -> None:
        self.api_key: str = api_key
        self.model: str = model
        self.endpoint: str = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

    def enrich_holiday(self, holiday: Holiday, country_name: str) -> Holiday:
        """
        Populate holiday.cultural_note and holiday.greeting via Gemini.

        Design decision:
        - Fails soft: on network errors, rate limits (HTTP 429), or timeouts,
          it sets `holiday.enrichment_error` while preserving `holiday.cultural_note = ""`
          so that the error is clearly displayed and the request can be retried on demand.

        Args:
            holiday: The Holiday instance to enrich in-place.
            country_name: Name of the country where the holiday is observed.

        Returns:
            The modified Holiday instance.
        """
        if not self.api_key:
            holiday.cultural_note = "No Gemini API key set — AI context unavailable."
            holiday.greeting = ""
            holiday.enrichment_error = "Missing API key"
            return holiday

        prompt = self._build_prompt(holiday, country_name)
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=15,
            )
            response.raise_for_status()
            data: Any = response.json()
            text: str = self._extract_text(data)
            parsed = self._parse_response(text)
            holiday.cultural_note = parsed.get("cultural_note", "")
            holiday.greeting = parsed.get("greeting", "")
            holiday.enrichment_error = None
        except Exception as exc:
            holiday.enrichment_error = f"Cultural context unavailable right now ({type(exc).__name__})."

        return holiday

    @staticmethod
    def _build_prompt(holiday: Holiday, country_name: str) -> str:
        """Construct the prompt instructing Gemini to return strict JSON with cultural notes."""
        return (
            f"Respond ONLY with JSON, no markdown fences, no preamble. "
            f"For the holiday '{holiday.name}' celebrated in {country_name}, "
            f"return a JSON object with keys: "
            f'"cultural_note" (2-3 sentences on its historical/cultural meaning), '
            f'"greeting" (a short appropriate greeting phrase, or empty string if none exists).'
        )

    @staticmethod
    def _parse_response(text: str) -> CultureResponse:
        """
        Parse raw model text output into a typed CultureResponse dictionary.
        Extracts JSON blocks even when enclosed in markdown backticks or preambles.
        """
        cleaned = text.strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        else:
            cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        parsed: Any = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise TypeError("Gemini response must be a JSON object.")
        cultural_note = parsed.get("cultural_note", "")
        greeting = parsed.get("greeting", "")
        if not isinstance(cultural_note, str) or not isinstance(greeting, str):
            raise TypeError("Gemini response fields must be strings.")
        return {"cultural_note": cultural_note, "greeting": greeting}

    @staticmethod
    def _extract_text(data: Any) -> str:
        """Extract candidate generated text from Gemini API response payload."""
        candidates = data["candidates"]
        text = candidates[0]["content"]["parts"][0]["text"]
        if not isinstance(text, str):
            raise TypeError("Gemini response text must be a string.")
        return text