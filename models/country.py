"""
Country data model representing a nation and its associated holiday schedule.
"""
from dataclasses import dataclass, field
from models.holiday import Holiday
from typing_defs import CountryData


@dataclass
class Country:
    """
    Represents a country, including its ISO alpha-2 code, human-readable name,
    the active calendar year, and the list of observed public holidays.

    Attributes:
        code: 2-letter uppercase ISO country code (e.g. 'NG', 'US', 'JP').
        name: Full English country name (e.g. 'Nigeria', 'United States').
        year: The calendar year corresponding to the holiday schedule.
        holidays: Collection of Holiday objects observed by this country.
    """
    code: str
    name: str = ""
    year: int | None = None
    holidays: list[Holiday] = field(default_factory=list)

    def add_holiday(self, holiday: Holiday) -> None:
        """Append a Holiday instance to the country's holiday list."""
        self.holidays.append(holiday)

    def sorted_holidays(self) -> list[Holiday]:
        """Return holidays sorted chronologically by date."""
        return sorted(self.holidays, key=lambda h: h.date)

    def to_dict(self) -> CountryData:
        """Serialize Country instance to a dictionary adhering to CountryData TypedDict."""
        return {
            "code": self.code,
            "name": self.name,
            "holidays": [h.to_dict() for h in self.sorted_holidays()],
        }