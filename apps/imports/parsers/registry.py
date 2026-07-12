"""Registry so parsers stay replaceable per data source (§15)."""

from .base import BaseParser


def get_parser(key: str) -> BaseParser:
    from .luebeck_gelber_sack import LuebeckGelberSackParser

    parsers: dict[str, type[BaseParser]] = {
        LuebeckGelberSackParser.key: LuebeckGelberSackParser,
    }
    if key not in parsers:
        raise KeyError(f"Unbekannter Parser: {key!r}. Verfügbar: {', '.join(parsers)}")
    return parsers[key]()
