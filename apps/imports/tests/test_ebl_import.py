"""End-to-end test of the EBL import against the archived sample PDF.

Verifies that the plan is applied to real zones/assignments and that house
numbers resolve to the correct tour – the key improvement over BMS sampling.
The full import is expensive, so all assertions share one run.
"""

from pathlib import Path

import pytest

from apps.addresses.models import AssignmentStatus, Street, StreetAssignment
from apps.core.text import normalize_street_name
from apps.imports.ebl_import import run_ebl_import
from apps.imports.models import ImportRunStatus
from apps.schedules.models import CollectionDate, CollectionZone

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "samples" / "abfuhrplan-ebl-2026.pdf"
pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="EBL-Beispiel-PDF nicht vorhanden")


def _resolve(street, house_number, slug):
    return {
        a.zone.code
        for a in StreetAssignment.objects.filter(
            street=street, zone__waste_type__slug=slug, status=AssignmentStatus.ACTIVE
        ).select_related("zone")
        if a.matches(house_number)
    }


def test_ebl_import_end_to_end(db):
    run = run_ebl_import(str(SAMPLE), publish=True)

    # 1. all four streams applied
    assert run.status in (ImportRunStatus.COMPLETED, ImportRunStatus.NEEDS_REVIEW)
    assert set(run.stats["waste_types"]) == {
        "restabfall", "bioabfall", "papier", "gelber-sack",
    }

    # 2. official letter zones replace the old BMS cluster codes
    for slug in ("gelber-sack", "restabfall", "bioabfall"):
        codes = set(CollectionZone.objects.filter(waste_type__slug=slug).values_list("code", flat=True))
        assert codes == set("ABCDEFGHIJ"), slug
    papier = set(CollectionZone.objects.filter(waste_type__slug="papier").values_list("code", flat=True))
    assert papier == set("ABCDEFGHIJKLMNOPQRST")
    assert not CollectionZone.objects.filter(code__startswith="R0").exists()

    # 3. the key win: a house-number split resolves to different tours
    kahl = Street.objects.filter(normalized_name=normalize_street_name("Kahlhorststraße")).first()
    assert kahl is not None
    low = _resolve(kahl, 3, "gelber-sack")
    high = _resolve(kahl, 30, "gelber-sack")
    assert low and high and low != high

    # 4. resolved zones actually carry dates
    achatweg = Street.objects.filter(normalized_name="achatweg").first()
    codes = _resolve(achatweg, 5, "restabfall")
    assert codes
    assert CollectionDate.objects.filter(
        zone__waste_type__slug="restabfall", zone__code__in=codes, date__year=2026
    ).count() >= 24

    # 5. old-town streets keep both weekly tours
    aegidien = Street.objects.filter(normalized_name=normalize_street_name("Aegidienstraße")).first()
    assert len(_resolve(aegidien, 1, "gelber-sack")) == 2
