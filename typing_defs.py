"""Shared typed data contracts exchanged between Holidex layers.

The definitions describe application-owned data at serialization and service
boundaries, while external JSON payloads are validated before they enter these types.
"""
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from models.holiday import Holiday


class HolidayData(TypedDict):
    name: str
    date: str
    type: str
    cultural_note: str
    greeting: str


class CountryData(TypedDict):
    code: str
    name: str
    holidays: list[HolidayData]


class NagerHolidayData(TypedDict):
    name: str
    date: str
    types: list[str]


class HolidayPair(TypedDict):
    a: "Holiday"
    b: "Holiday"


class ComparisonResult(TypedDict):
    country_a: str
    country_b: str
    same_date: list[HolidayPair]
    shared_celebrations: list[HolidayPair]
    unique_to_a: list["Holiday"]
    unique_to_b: list["Holiday"]


class CultureResponse(TypedDict):
    cultural_note: str
    greeting: str
