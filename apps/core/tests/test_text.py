from apps.core.text import collapse_letter_spacing, normalize_street_name, parse_house_number


def test_collapse_letter_spacing():
    # Sperrschrift-Zeilen aus dem offiziellen PDF (Seite 2)
    assert collapse_letter_spacing("K a h l h o r s t s t r .") == "Kahlhorststr."
    assert collapse_letter_spacing("A m B a c h") == "Am Bach"
    assert collapse_letter_spacing("A n d e r B ä k") == "An der Bäk"
    assert collapse_letter_spacing("A u f d e m B a g g e r s a n d") == "Auf dem Baggersand"
    assert collapse_letter_spacing("K a h l h o r s t s t r . 1 - 1 5 / 1 6") == "Kahlhorststr. 1-15/16"
    # teilverschmolzene Fragmente
    assert collapse_letter_spacing("Dröge st r.") == "Drögestr."
    assert collapse_letter_spacing("B e e re nweg") == "Beerenweg"
    # normale Namen bleiben unangetastet
    assert collapse_letter_spacing("Beidendorfer Hauptstr.") == "Beidendorfer Hauptstr."
    assert collapse_letter_spacing("Vorderreihe") == "Vorderreihe"
    assert collapse_letter_spacing("Karl-Roß-Weg") == "Karl-Roß-Weg"


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
