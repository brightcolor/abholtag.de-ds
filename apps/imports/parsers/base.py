"""Parser interfaces – parsers are decoupled from views and models (§5, §15)."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Issue:
    level: str  # info | warning | error
    code: str
    message: str

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message}


@dataclass
class CalendarEntry:
    date: date
    zone_code: str
    kind: str = "regular"  # regular | shifted | special
    note: str = ""


@dataclass
class StreetEntry:
    name: str
    district: str = ""
    zone_codes: list[str] = field(default_factory=list)
    raw_range: str = ""
    note: str = ""


@dataclass
class ParsedPlan:
    year: int | None = None
    calendar: list[CalendarEntry] = field(default_factory=list)
    streets: list[StreetEntry] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def add_issue(self, level: str, code: str, message: str) -> None:
        self.issues.append(Issue(level, code, message))

    @property
    def has_blocking_issues(self) -> bool:
        return any(i.level == "error" for i in self.issues)


class BaseParser:
    """A parser turns one source document into a ParsedPlan."""

    key: str = ""

    def parse(self, path: str) -> ParsedPlan:  # pragma: no cover - interface
        raise NotImplementedError
