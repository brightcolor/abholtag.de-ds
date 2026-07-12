from apps.core.text import normalize_street_name, parse_house_number


def test_strasse_variants_normalize_identically():
    variants = ["Musterstraße", "Musterstrasse", "Musterstr.", "MUSTERSTRASSE", "Muster Straße"]
    normalized = {normalize_street_name(v) for v in variants}
    assert normalized == {"musterstrasse"}


def test_sankt_and_hyphens():
    assert normalize_street_name("St. Jürgen-Ring") == normalize_street_name("Sankt Jürgen Ring")


def test_umlauts():
    assert normalize_street_name("Möllerung") == "moellerung"
    assert normalize_street_name("Große Burgstraße") == normalize_street_name("Grosse Burgstr.")


def test_parse_house_number():
    assert parse_house_number("12") == (12, "")
    assert parse_house_number("12a") == (12, "a")
    assert parse_house_number(" 7 B ") == (7, "b")
    assert parse_house_number("") == (None, "")
    assert parse_house_number("abc") == (None, "")
