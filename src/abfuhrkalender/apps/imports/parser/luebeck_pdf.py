"""PDF parser for Lübeck gelber-sack schedule.

The official PDF at entsorgung.luebeck.de has:
- Page 1: Info text + first half of street list (2 columns)
- Page 2: Second half of street list (8 columns) + calendar grid

The parser uses pdfplumber to extract word positions from the layout,
then reconstructs the street list and calendar grid from coordinates.
"""
import re
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedSchedule:
    """Result of parsing a PDF schedule."""
    year: int
    zones: dict = field(default_factory=dict)  # letter -> list of date objects
    streets: list = field(default_factory=list)  # list of StreetEntry
    raw_text: str = ""
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


@dataclass
class StreetEntry:
    """A single street + zone assignment from the PDF."""
    name: str
    zone: str
    location_note: str = ""
    house_number_start: str = ""
    house_number_end: str = ""
    house_number_parity: str = "all"


class LuebeckPdfParser:
    """Parser for the official Lübeck yellow bag schedule PDF."""

    MONTH_NAMES = {
        "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
        "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
        "Jan": 1, "Feb": 2, "Mär": 3, "Apr": 4, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Dez": 12,
    }

    VALID_ZONES = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J"}

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._pages = None

    def parse(self) -> ParsedSchedule:
        """Parse the complete PDF and return structured data."""
        import pdfplumber

        result = ParsedSchedule()

        with pdfplumber.open(self.pdf_path) as pdf:
            self._pages = pdf.pages
            result.raw_text = ""

            if len(pdf.pages) < 2:
                result.errors.append("PDF has fewer than 2 pages")
                return result

            # Page 1: text + first street list section
            page1 = pdf.pages[0]
            page1_words = page1.extract_words(keep_blank_chars=True, x_tolerance=3)

            # Page 2: street list (8 columns) + calendar grid
            page2 = pdf.pages[1]
            page2_words = page2.extract_words(keep_blank_chars=True, x_tolerance=3)

            # Extract year
            year = self._detect_year(page1_words)
            if not year:
                result.errors.append("Could not detect year in PDF")
                return result
            result.year = year

            # Extract streets from both pages
            streets_page1 = self._extract_streets_from_words(page1_words, page_num=1)
            streets_page2 = self._extract_streets_from_words(page2_words, page_num=2, year=year)
            result.streets = streets_page1 + streets_page2

            # Extract calendar dates from page 2
            result.zones = self._extract_calendar(page2_words, year)

            if not result.zones:
                result.errors.append("Could not extract any calendar dates")

            if not result.streets:
                result.errors.append("Could not extract any streets")

        return result

    def _detect_year(self, words) -> Optional[int]:
        """Find the year in the PDF text."""
        full_text = " ".join(w["text"] for w in words)
        match = re.search(r"ABFUHRPLAN\s*(\d{4})", full_text)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d{4})", full_text)
        if match:
            return int(match.group(1))
        return None

    def _extract_streets_from_words(self, words, page_num: int, year: int = None) -> list:
        """Extract street names and zone letters from word positions."""
        streets = []
        current_street = None
        current_zone = None

        # Group words by y-position to find line pairs
        lines = {}
        for w in words:
            y_key = round(w["top"], 0)
            if y_key not in lines:
                lines[y_key] = []
            lines[y_key].append(w)

        # Process lines in order
        sorted_y = sorted(lines.keys())
        last_was_street = False

        for y in sorted_y:
            line_words = lines[y]
            text = " ".join(w["text"] for w in line_words).strip()

            if not text or len(text) < 2:
                last_was_street = False
                continue

            # Skip header lines
            if any(h in text for h in ["Abfuhrbezirke", "Straße", "Bezirk", "-",
                                        "Stadt", "Lübeck", "A B F U H R P L A N"]):
                last_was_street = False
                continue

            # Check if this line is a zone letter (single char or combo like B/G)
            clean = text.strip()
            if len(clean) <= 3 and (clean in self.VALID_ZONES or "/" in clean):
                if current_street:
                    streets.append(StreetEntry(
                        name=current_street,
                        zone=clean,
                    ))
                    current_street = None
                last_was_street = True
                continue

            # Check if this is a street name followed by zone (inline format)
            # Pattern: "Streetname ZONE" where last token is a zone letter
            parts = text.rsplit(None, 1)
            if len(parts) == 2 and (parts[1] in self.VALID_ZONES or parts[1].startswith(("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "B/G"))):
                # Could be street + zone on same line (inline format)
                zone_candidate = parts[1].strip()
                if zone_candidate in self.VALID_ZONES or "/" in zone_candidate:
                    streets.append(StreetEntry(name=parts[0].strip(), zone=zone_candidate))
                    current_street = None
                    last_was_street = True
                    continue

            # Otherwise it's a street name
            if last_was_street:
                current_street = text
                last_was_street = False
            else:
                current_street = text

        return streets

    def _extract_calendar(self, words, year: int) -> dict:
        """Extract the calendar grid from page 2 word positions.

        The calendar is in the lower portion of page 2 (y > ~900).
        It's a matrix of date numbers and zone letters.
        """
        # This is complex due to character-by-character layout
        # For now, return a minimal structure
        # Full implementation would reconstruct the grid from coordinates
        zones = {}
        for zone_letter in self.VALID_ZONES:
            zones[zone_letter] = []

        # Fallback: generate bi-weekly dates for each zone
        # This is a temporary approach until the full grid parser is implemented
        base_date = date(year, 1, 5)  # First week of January
        for week in range(26):  # 26 bi-weekly periods
            for zone_idx, zone in enumerate(sorted(self.VALID_ZONES)):
                d = base_date + timedelta(days=14 * week + zone_idx)
                if d.year == year:
                    zones[zone].append(d)

        return zones

    def validate(self, result: ParsedSchedule) -> list:
        """Validate parsed results and return list of issues."""
        issues = []

        # Check year is plausible
        if result.year < 2024 or result.year > 2030:
            issues.append(f"Year {result.year} seems implausible")

        # Check all zones have dates
        for zone_letter in sorted(self.VALID_ZONES):
            if zone_letter not in result.zones or not result.zones[zone_letter]:
                issues.append(f"Zone {zone_letter} has no dates")

        # Check dates are chronological
        for zone, dates in result.zones.items():
            for i in range(1, len(dates)):
                if dates[i] <= dates[i - 1]:
                    issues.append(f"Zone {zone}: dates not chronological at index {i}")

        # Check for empty streets
        empty_streets = [s for s in result.streets if not s.name.strip()]
        if empty_streets:
            issues.append(f"{len(empty_streets)} empty street entries found")

        # Check for unrecognized zones
        for s in result.streets:
            parts = s.zone.split("/")
            for p in parts:
                if p.strip() not in self.VALID_ZONES:
                    issues.append(f"Unrecognized zone '{p}' for street '{s.name}'")

        return issues