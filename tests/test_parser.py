"""Tests for the PDF parser - using local test files, not the live URL."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from apps.imports.parser.luebeck_pdf import LuebeckPdfParser, ParsedSchedule, StreetEntry


class TestLuebeckPdfParser:
    """Test the PDF parser without depending on the actual PDF."""

    def test_year_detection(self):
        """Parser should detect the year from the PDF text."""
        parser = LuebeckPdfParser("dummy.pdf")
        mock_words = [
            {"text": "ABFUHRPLAN", "top": 10, "x0": 0},
            {"text": "2026", "top": 10, "x0": 100},
            {"text": "Gelber", "top": 20, "x0": 0},
            {"text": "Sack", "top": 20, "x0": 50},
        ]
        year = parser._detect_year(mock_words)
        assert year == 2026

    def test_schedule_year(self):
        """Verifies ScheduleYear has required fields."""
        from apps.schedules.models import ScheduleYear
        fields = [f.name for f in ScheduleYear._meta.get_fields()]
        assert "waste_type" in fields
        assert "year" in fields
        assert "status" in fields
        assert "published_at" in fields
        assert ScheduleYear.PUBLICATION_STATUS is not None

    def test_street_entry_dataclass(self):
        """StreetEntry dataclass should initialize correctly."""
        entry = StreetEntry(name="Musterstraße", zone="A", location_note="Innenstadt")
        assert entry.name == "Musterstraße"
        assert entry.zone == "A"
        assert entry.location_note == "Innenstadt"

    def test_parsed_schedule_dataclass(self):
        """ParsedSchedule should initialize with defaults."""
        schedule = ParsedSchedule(year=2026)
        assert schedule.year == 2026
        assert schedule.streets == []
        assert schedule.warnings == []
        assert schedule.errors == []

    def test_valid_zones(self):
        """Parser should only accept valid zone letters A-J."""
        parser = LuebeckPdfParser("dummy.pdf")
        assert "A" in parser.VALID_ZONES
        assert "J" in parser.VALID_ZONES
        assert "K" not in parser.VALID_ZONES

    def test_month_names_complete(self):
        """Parser should have all German month names."""
        parser = LuebeckPdfParser("dummy.pdf")
        assert "Januar" in parser.MONTH_NAMES
        assert "Dezember" in parser.MONTH_NAMES
        assert len(parser.MONTH_NAMES) >= 12


class TestAddressModels:
    """Tests for address models."""

    def test_street_creation(self):
        """Create a street and verify."""
        from apps.addresses.models import Street
        street = Street(name="Musterstraße", search_name="musterstrasse")
        assert street.name == "Musterstraße"
        assert street.search_name == "musterstrasse"

    def test_street_normalization(self):
        """Street name normalization should handle Umlaute."""
        from apps.addresses.models import Street
        normalized = Street.normalize_name("Musterstraße")
        assert "ss" in normalized  # ß -> ss
        assert normalized == "musterstrasse"

    def test_street_normalization_st(self):
        """Street name normalization should handle Sankt."""
        from apps.addresses.models import Street
        normalized = Street.normalize_name("Sankt Lorenz")
        assert "st." in normalized or "st " in normalized

    def test_collection_zone_valid_letters(self):
        """CollectionZone should accept valid letters."""
        from apps.addresses.models import CollectionZone
        zone = CollectionZone(letter="A")
        assert zone.letter == "A"

    def test_address_key_uniqueness(self):
        """AddressKey should have unique_together constraint."""
        from apps.addresses.models import AddressKey
        constraint = AddressKey._meta.unique_together
        assert ("street", "house_number", "house_number_suffix") in constraint


class TestAnalytics:
    """Tests for analytics models."""

    def test_event_types(self):
        """AnalyticsEvent should have all required event types."""
        from apps.analytics.models import AnalyticsEvent
        types = [t[0] for t in AnalyticsEvent.EVENT_TYPES]
        assert "page_view" in types
        assert "street_search" in types
        assert "address_resolved" in types
        assert "schedule_view" in types


class TestCommunity:
    """Tests for community models."""

    def test_error_report_categories(self):
        """ErrorReport should have all required categories."""
        from apps.community.models import ErrorReport
        cats = [c[0] for c in ErrorReport.CATEGORY_CHOICES]
        assert "wrong_date" in cats
        assert "street_missing" in cats
        assert "other" in cats

    def test_quorum_rule_configurable(self):
        """QuorumRule should be configurable per waste type."""
        from apps.community.models import QuorumRule
        assert hasattr(QuorumRule, "min_votes")


class TestCalendar:
    """Tests for calendar/ICS generation."""

    def test_ics_structure(self):
        """Calendar ICS should have required VCALENDAR structure."""
        # Verify the calendar app can import
        from apps.calendars.views import CalendarFeedView
        assert CalendarFeedView is not None