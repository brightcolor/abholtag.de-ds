"""Address resolution: street + house number → zones (§10)."""

from dataclasses import dataclass, field

from django.db.models import Q

from apps.core.text import normalize_street_name

from .models import AddressKey, AssignmentStatus, Street, StreetAssignment


def search_streets(query: str, limit: int = 12):
    """Tolerant autocomplete over streets and aliases."""
    normalized = normalize_street_name(query)
    if len(normalized) < 2:
        return Street.objects.none()
    return (
        Street.objects.filter(
            Q(normalized_name__icontains=normalized) | Q(aliases__normalized_name__icontains=normalized),
            is_active=True,
        )
        .select_related("district", "city")
        .distinct()
        .order_by("normalized_name")[:limit]
    )


@dataclass
class ResolutionResult:
    street: Street | None = None
    zones: list = field(default_factory=list)
    needs_house_number: bool = False
    ambiguous_streets: list = field(default_factory=list)
    address_key: AddressKey | None = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.zones) and self.address_key is not None


def street_requires_house_number(street: Street) -> bool:
    """A house number is required when assignments differ by range (§10)."""
    active = street.assignments.filter(status=AssignmentStatus.ACTIVE)
    return active.exclude(house_from__isnull=True).exists()


def resolve_address(
    street: Street, house_number: int | None, suffix: str = "", waste_type=None
) -> ResolutionResult:
    result = ResolutionResult(street=street)
    assignments = street.assignments.filter(status=AssignmentStatus.ACTIVE).select_related(
        "zone", "zone__waste_type"
    )
    if waste_type is not None:
        assignments = assignments.filter(zone__waste_type=waste_type)

    if street_requires_house_number(street) and house_number is None:
        result.needs_house_number = True
        result.error = "Für diese Straße wird eine Hausnummer benötigt."
        return result

    matching = [a for a in assignments if a.matches(house_number)]
    if not matching:
        # Unclear assignments must never be guessed (§10).
        result.error = "Für diese Adresse liegt keine eindeutige Tourenzuordnung vor."
        return result

    zones = {a.zone_id: a.zone for a in matching}
    result.zones = sorted(zones.values(), key=lambda z: z.code)
    result.address_key, _ = AddressKey.objects.get_or_create(
        street=street, house_number=house_number, suffix=suffix or ""
    )
    return result


def zones_for_address_key(address_key: AddressKey, waste_type=None):
    assignments = StreetAssignment.objects.filter(
        street=address_key.street, status=AssignmentStatus.ACTIVE
    ).select_related("zone", "zone__waste_type")
    if waste_type is not None:
        assignments = assignments.filter(zone__waste_type=waste_type)
    zones = {a.zone_id: a.zone for a in assignments if a.matches(address_key.house_number)}
    return sorted(zones.values(), key=lambda z: z.code)
