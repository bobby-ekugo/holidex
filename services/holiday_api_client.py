"""
HolidayAPIClient: client service for querying the Nager.Date v3 REST API.

Handles:
- Fetching and parsing public holiday lists for given countries and years
- Resolving ISO country codes to country names via AvailableCountries endpoint
- Translating HTTP status codes into domain-specific HolidexError exceptions
"""
from datetime import date
from typing import Any
import requests

from config import NAGER_BASE_URL
from models.holiday import Holiday
from exceptions import UnsupportedCountryError, APIRequestError


class HolidayAPIClient:
    """
    HTTP client for the Nager.Date v3 holiday API.

    Attributes:
        base_url: Root endpoint URL for Nager.Date API v3.
        timeout: Network timeout in seconds for HTTP requests.
    """
    def __init__(self, base_url: str = NAGER_BASE_URL, timeout: int = 10) -> None:
        self.base_url: str = base_url
        self.timeout: int = timeout
        self._countries_cache: dict[str, str] | None = None

    def get_available_countries(self) -> dict[str, str]:
        """
        Fetch and cache all countries supported by Nager.Date.

        Returns:
            Dictionary mapping uppercase 2-letter country codes to full country names
            (e.g. {'NG': 'Nigeria', 'US': 'United States'}). Returns empty dict on failure.
        """
        if self._countries_cache is not None:
            return self._countries_cache
        url = f"{self.base_url}/AvailableCountries"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                self._countries_cache = {
                    str(item["countryCode"]).upper(): str(item["name"])
                    for item in data
                    if isinstance(item, dict) and "countryCode" in item and "name" in item
                }
                return self._countries_cache
        except Exception:
            pass
        return {}

    def get_country_name(self, country_code: str) -> str:
        """
        Resolve an ISO country code to its full English country name.

        Args:
            country_code: 2-letter ISO code (e.g. 'NG', 'US').

        Returns:
            The country name if found, or an empty string if unmapped.
        """
        countries = self.get_available_countries()
        return countries.get(country_code.upper(), "")

    def get_holidays(self, country_code: str, year: int) -> list[Holiday]:
        """
        Retrieve public holidays for a specific country and year.

        Args:
            country_code: 2-letter ISO code (e.g. 'NG', 'US').
            year: 4-digit calendar year (e.g. 2026).

        Returns:
            List of parsed Holiday domain objects.

        Raises:
            UnsupportedCountryError: If the API returns HTTP 404 for the country code.
            APIRequestError: If network fails, HTTP error occurs, or response JSON is malformed.
        """
        url = f"{self.base_url}/PublicHolidays/{year}/{country_code}"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if response.status_code == 404:
                raise UnsupportedCountryError(country_code) from exc
            raise APIRequestError(f"Nager.Date API error: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise APIRequestError(f"Could not reach Nager.Date API: {exc}") from exc

        # Handle 204 No Content or empty responses gracefully
        if response.status_code == 204 or not response.text.strip():
            return []

        try:
            raw_data: Any = response.json()
        except ValueError as exc:
            raise APIRequestError("Nager.Date API returned malformed JSON.") from exc

        if not isinstance(raw_data, list):
            raise APIRequestError("Nager.Date API returned an unexpected data format.")

        try:
            return [self._parse_holiday(item) for item in raw_data]
        except (KeyError, TypeError, ValueError) as exc:
            raise APIRequestError("Nager.Date API returned invalid holiday data.") from exc

    @staticmethod
    def _parse_holiday(item: object) -> Holiday:
        """
        Validate and deserialize a single Nager.Date JSON holiday entry into a Holiday object.

        Args:
            item: Raw JSON object (dict) representing a holiday record from Nager.Date.

        Returns:
            A populated Holiday instance.

        Raises:
            TypeError: If the schema or types do not match expected contracts.
        """
        if not isinstance(item, dict):
            raise TypeError("Holiday payload must be an object.")
        name = item.get("name")
        holiday_date = item.get("date")
        holiday_types = item.get("types", [])
        if not isinstance(name, str) or not isinstance(holiday_date, str):
            raise TypeError("Holiday name and date must be strings.")
        if not isinstance(holiday_types, list) or not all(isinstance(value, str) for value in holiday_types):
            raise TypeError("Holiday types must be a list of strings.")

        return Holiday(
            name=name,
            date=date.fromisoformat(holiday_date),
            holiday_type=", ".join(holiday_types) or "Public",
        )