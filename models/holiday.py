"""
Holiday data model representing an individual public holiday or cultural observance.
"""
from dataclasses import dataclass
from datetime import date
from typing import Mapping, cast

from typing_defs import HolidayData


@dataclass
class Holiday:
    """
    Represents a single holiday event.

    Attributes:
        name: Name of the holiday (e.g. 'New Year\'s Day', 'Good Friday').
        date: Calendar date of observance.
        holiday_type: Category or classification (e.g. 'Public', 'Optional', 'Bank').
        cultural_note: Historical context or cultural meaning provided by Gemini API.
        greeting: Appropriate greeting or salute associated with the holiday.
        enrichment_error: Error description if cultural context retrieval failed (allows retrying).
    """
    name: str
    date: date
    holiday_type: str
    cultural_note: str = ""
    greeting: str = ""
    enrichment_error: str | None = None

    def to_dict(self) -> HolidayData:
        """Serialize Holiday instance into a dictionary adhering to HolidayData TypedDict."""
        return cast(HolidayData, {
            "name": self.name,
            "date": self.date.isoformat() if isinstance(self.date, date) else str(self.date),
            "type": self.holiday_type,
            "cultural_note": self.cultural_note,
            "greeting": self.greeting,
        })

    @classmethod
    def from_dict(cls, data: Mapping[str, str]) -> "Holiday":
        """Reconstruct a Holiday instance from a dictionary representation."""
        return cls(
            name=data["name"],
            date=date.fromisoformat(data["date"]),
            holiday_type=data.get("type", ""),
            cultural_note=data.get("cultural_note", ""),
            greeting=data.get("greeting", ""),
        )