"""
FileManager: saves favourites (JSON), holiday guides and comparison
results (Markdown) to local files.
"""
import json
import os
from datetime import datetime

from config import DATA_DIR, FAVOURITES_FILE, GUIDES_DIR, COMPARISONS_DIR
from models.country import Country
from exceptions import StorageError
from typing_defs import ComparisonResult


class FileManager:
    """Create storage directories and read or write Holidex user artifacts."""

    def __init__(self) -> None:
        """Ensure the favourites, guides, and comparisons directories exist."""
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(GUIDES_DIR, exist_ok=True)
        os.makedirs(COMPARISONS_DIR, exist_ok=True)

    # --- Favourites ---
    def load_favourites(self) -> list[str]:
        """Return saved country codes, raising StorageError for invalid files."""
        if not os.path.exists(FAVOURITES_FILE):
            return []
        try:
            with open(FAVOURITES_FILE, "r", encoding="utf-8") as f:
                favourites = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            raise StorageError(f"Could not load favourites: {exc}") from exc
        if not isinstance(favourites, list) or not all(isinstance(code, str) for code in favourites):
            raise StorageError("Could not load favourites: expected a list of country codes.")
        return favourites

    def save_favourite(self, country_code: str) -> None:
        """Add a country code to the favourites JSON file if it is not present."""
        favourites = self.load_favourites()
        if country_code not in favourites:
            favourites.append(country_code)
        try:
            with open(FAVOURITES_FILE, "w", encoding="utf-8") as f:
                json.dump(favourites, f, indent=2)
        except OSError as exc:
            raise StorageError(f"Could not save favourite: {exc}") from exc

    # --- Holiday guide (Markdown) ---
    def save_guide(self, country: Country, year: int) -> str:
        """Write a country's holiday schedule and available context to Markdown."""
        filename = f"{country.code}_{year}_{self._timestamp()}.md"
        path = os.path.join(GUIDES_DIR, filename)
        country_label = f"{country.name} ({country.code})" if country.name else country.code
        lines = [f"# Holiday Guide: {country_label} ({year})", ""]
        for h in country.sorted_holidays():
            lines.append(f"## {h.name} — {h.date.isoformat()} ({h.holiday_type})")
            if h.cultural_note:
                lines.append(f"{h.cultural_note}")
            if h.greeting:
                lines.append(f"\n**Greeting:** {h.greeting}")
            lines.append("")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError as exc:
            raise StorageError(f"Could not save guide: {exc}") from exc
        return path

    # --- Comparison result (Markdown) ---
    def save_comparison(self, comparison: ComparisonResult) -> str:
        """Write a comparison result to a uniquely named Markdown report."""
        a, b = comparison["country_a"], comparison["country_b"]
        filename = f"{a}_vs_{b}_{self._timestamp()}.md"
        path = os.path.join(COMPARISONS_DIR, filename)

        lines = [f"# Comparison: {a} vs {b}", ""]

        lines.append("## Overlapping Dates")
        for pair in comparison["same_date"]:
            lines.append(f"- {pair['a'].date.isoformat()}: {pair['a'].name} / {pair['b'].name}")
        lines.append("")

        lines.append("## Shared Celebrations")
        for pair in comparison["shared_celebrations"]:
            lines.append(
                f"- {pair['a'].name} ({pair['a'].date.isoformat()}) "
                f"vs {pair['b'].name} ({pair['b'].date.isoformat()})"
            )
        lines.append("")

        lines.append(f"## Unique to {a}")
        for h in comparison["unique_to_a"]:
            lines.append(f"- {h.date.isoformat()}: {h.name}")
        lines.append("")

        lines.append(f"## Unique to {b}")
        for h in comparison["unique_to_b"]:
            lines.append(f"- {h.date.isoformat()}: {h.name}")

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError as exc:
            raise StorageError(f"Could not save comparison: {exc}") from exc
        return path

    @staticmethod
    def _timestamp() -> str:
        """Return a filesystem-friendly timestamp with microsecond precision."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")