"""
Input validation functions for country codes and calendar years.

Enforces format conventions and range limits before making upstream API requests.
"""
import re
from exceptions import InvalidCountryCodeError, InvalidYearError

# Regex pattern matching exactly two alphabetic characters (ISO 3166-1 alpha-2)
COUNTRY_CODE_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z]{2}$")

# Regex pattern matching exactly 4 decimal digits
YEAR_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}$")

# Supported year range aligned with public holiday API capabilities
MIN_YEAR: int = 1980
MAX_YEAR: int = 2075


def validate_country_code(code: str | None) -> str:
    """
    Validate and normalize an ISO 3166-1 alpha-2 country code.

    Args:
        code: Raw string input representing the 2-letter country code.

    Returns:
        The normalized uppercase 2-letter country code (e.g. 'NG', 'US').

    Raises:
        InvalidCountryCodeError: If code is None, empty, or does not match exactly two letters.
    """
    if code is None:
        raise InvalidCountryCodeError("Country code cannot be empty.")
    cleaned = code.strip().upper()
    if not COUNTRY_CODE_PATTERN.match(cleaned):
        raise InvalidCountryCodeError(
            f"'{code}' is not a valid country code. Use a 2-letter ISO code, e.g. NG, US, GB."
        )
    return cleaned


def validate_year(year: str | int) -> int:
    """
    Validate that an input represents a 4-digit calendar year within supported bounds.

    Args:
        year: String or integer representation of a 4-digit year.

    Returns:
        The validated integer year between MIN_YEAR and MAX_YEAR inclusive.

    Raises:
        InvalidYearError: If input is not 4 digits, equals '0000', or falls outside 1980–2075.
    """
    year_str = str(year).strip()
    if not YEAR_PATTERN.match(year_str) or year_str == "0000":
        raise InvalidYearError(f"'{year}' is not a valid 4-digit year, e.g. 2026.")
    year_int = int(year_str)
    if year_int < MIN_YEAR or year_int > MAX_YEAR:
        raise InvalidYearError(
            f"Year '{year}' is out of supported range. Please enter a year between {MIN_YEAR} and {MAX_YEAR}."
        )
    return year_int