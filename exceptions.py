"""
Custom exception hierarchy for Holidex.

All domain-specific errors inherit from HolidexError, allowing UI and
service layers to distinguish application errors from unexpected system faults.
"""


class HolidexError(Exception):
    """Base exception for all domain and operational errors in Holidex."""
    pass


class InvalidCountryCodeError(HolidexError):
    """
    Raised when an input country code violates syntax requirements.
    Expected format: 2-letter alphabetic ISO 3166-1 alpha-2 code (e.g. 'NG', 'US', 'GB').
    """
    pass


class InvalidYearError(HolidexError):
    """
    Raised when an input year is malformed or outside the supported range (1980–2075).
    """
    pass


class UnsupportedCountryError(HolidexError):
    """
    Raised when a country code is syntactically valid but not recognized or supported
    by the upstream holiday provider (e.g., HTTP 404 from Nager.Date).
    """
    def __init__(self, country_code: str):
        self.country_code: str = country_code
        super().__init__(f"Country '{country_code}' is not supported by the holiday API.")


class APIRequestError(HolidexError):
    """
    Raised when an HTTP or network communication error occurs during an external
    API request (such as Nager.Date or Google Gemini API timeouts, connection drops, or HTTP 5xx).
    """
    pass


class StorageError(HolidexError):
    """
    Raised when persisting or retrieving data from the local filesystem fails
    (e.g., permission denied, corrupted JSON, missing storage directories).
    """
    pass