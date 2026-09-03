"""
HolidayComparator: compares two Country objects' holiday lists.
Uses substantive keyword-overlap matching with robust stop-word filtering
and 1-to-1 pairing to prevent false positives and Cartesian explosions.
"""
import re
from models.country import Country
from models.holiday import Holiday
from typing_defs import ComparisonResult, HolidayPair

STOP_WORDS: set[str] = {
    "day", "days", "the", "of", "and", "in", "for", "a", "an", "at", "on", "to",
    "national", "state", "public", "bank", "holiday", "holidays", "federal",
    "memorial", "international", "annual", "observance", "celebration",
    "feast", "saint", "st", "eve", "new", "first", "second", "third", "fourth",
    "official", "general", "special", "birthday", "birth", "anniversary", "s",
}


class HolidayComparator:
    """
    Comparator engine for discovering overlaps, shared cultural traditions,
    and distinct holidays between two countries.

    Comparison workflow:
    1. Exact Date Matching: Holidays sharing the identical calendar date are paired first.
    2. Shared Celebrations: Holidays on different dates whose substantive keyword tokens
       overlap (e.g. 'Thanksgiving' vs 'Thanksgiving Day') are paired 1-to-1.
    3. Unique Holidays: Unmatched holidays are categorized as unique to their respective country.
    """

    def compare(self, country_a: Country, country_b: Country) -> ComparisonResult:
        """
        Compare public holiday calendars for two countries.

        Args:
            country_a: First Country instance populated with holidays.
            country_b: Second Country instance populated with holidays.

        Returns:
            A ComparisonResult dictionary containing:
            - country_a: Code of first country.
            - country_b: Code of second country.
            - same_date: List of HolidayPair objects sharing the same calendar date.
            - shared_celebrations: List of HolidayPair objects sharing substantive celebration themes.
            - unique_to_a: List of holidays unique to Country A.
            - unique_to_b: List of holidays unique to Country B.
        """
        same_date: list[HolidayPair] = []
        shared_celebrations: list[HolidayPair] = []
        matched_a: set[int] = set()
        matched_b: set[int] = set()

        # Phase 1: Match by exact date
        b_by_date: dict[object, list[Holiday]] = {}
        for hb in country_b.holidays:
            b_by_date.setdefault(hb.date, []).append(hb)

        for ha in country_a.holidays:
            if id(ha) in matched_a:
                continue
            candidates = [hb for hb in b_by_date.get(ha.date, []) if id(hb) not in matched_b]
            if not candidates:
                continue

            # Prefer exact name match, then keyword overlap, then first candidate
            exact_match = next(
                (hb for hb in candidates if hb.name.strip().lower() == ha.name.strip().lower()), None
            )
            overlap_match = next((hb for hb in candidates if self._names_overlap(ha.name, hb.name)), None)
            best_hb = exact_match or overlap_match or candidates[0]

            same_date.append({"a": ha, "b": best_hb})
            matched_a.add(id(ha))
            matched_b.add(id(best_hb))

        # Phase 2: Match by shared celebrations (substantive keyword overlap, distinct dates)
        for ha in country_a.holidays:
            if id(ha) in matched_a:
                continue
            for hb in country_b.holidays:
                if id(hb) in matched_b:
                    continue
                if self._names_overlap(ha.name, hb.name):
                    shared_celebrations.append({"a": ha, "b": hb})
                    matched_a.add(id(ha))
                    matched_b.add(id(hb))
                    break

        # Phase 3: Unique to each country
        unique_to_a: list[Holiday] = [ha for ha in country_a.holidays if id(ha) not in matched_a]
        unique_to_b: list[Holiday] = [hb for hb in country_b.holidays if id(hb) not in matched_b]

        unique_to_a = self._dedup_holidays(unique_to_a)
        unique_to_b = self._dedup_holidays(unique_to_b)

        return {
            "country_a": country_a.code,
            "country_b": country_b.code,
            "same_date": same_date,
            "shared_celebrations": shared_celebrations,
            "unique_to_a": unique_to_a,
            "unique_to_b": unique_to_b,
        }

    @staticmethod
    def _extract_keywords(name: str) -> set[str]:
        """
        Extract meaningful keyword tokens from a holiday name.
        Removes possessives ('s), punctuation, and generic stop words.
        """
        cleaned = re.sub(r"['’]s\b|['’]", "", name.lower())
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        words = {w for w in cleaned.split() if len(w) > 1}
        return words - STOP_WORDS

    @classmethod
    def _names_overlap(cls, name_a: str, name_b: str) -> bool:
        """
        Determine if two holiday names share a substantive celebration theme.
        Returns True for identical names or non-empty substantive keyword overlap.
        """
        if name_a.strip().lower() == name_b.strip().lower():
            return True
        keywords_a = cls._extract_keywords(name_a)
        keywords_b = cls._extract_keywords(name_b)
        overlap = keywords_a & keywords_b
        return len(overlap) > 0

    @staticmethod
    def _dedup_holidays(holidays: list[Holiday]) -> list[Holiday]:
        """Deduplicate holiday entries having identical name and date within a list."""
        seen: set[tuple[str, str]] = set()
        result: list[Holiday] = []
        for h in holidays:
            key = (h.name.strip().lower(), h.date.isoformat())
            if key not in seen:
                seen.add(key)
                result.append(h)
        return result