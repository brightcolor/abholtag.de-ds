"""Parser for the official EBL "Wegweiser" PDF (all waste streams).

The document (analysed: 2026 edition, ~32 pages) is fully text based –
unlike the Veolia "Gelber Sack" PDF no OCR is required.

Relevant parts:

* Calendar spread (two identical copies, one to tear out): 12 month
  columns, one row per day. Each collection day carries THREE tour
  letters:

      column 1  A–J   Restmüll- UND Biotonne (same tour, same day)
      column 2  A–T   Kommunale Lübecker Altpapiertonne (every 4 weeks)
      column 3  A–J   Gelber Sack (Veolia)

* Street index (~1300 rows over many pages, three layout columns per
  page): street name, optional house-number ranges ("1-23 + 2-22a"),
  then the three tour letters. Old-town streets may carry split codes
  ("G/Q" = both tours, i.e. weekly collection).

Robustness principles (the plan changes every year):

* Nothing is keyed on page numbers, month header words or the year –
  calendar pages and index pages are detected by their content.
* Month columns are found by x-clustering the day cells; every column is
  then verified against the real calendar (weekday of each day number
  must match). A misdetected column can therefore never pass silently.
* Letters are assigned to their stream by x-slot calibration per month
  column, so single-letter cells (holiday make-up days) land in the
  correct stream.

The parser never writes to the database (§15). `parse_multi()` returns
one ParsedPlan per waste-type slug; `parse()` is kept for the BaseParser
interface and returns the combined plan of the Gelber Sack stream.
"""

import calendar as calendar_mod
import logging
import re
import statistics
from collections import Counter
from datetime import date

from .base import BaseParser, CalendarEntry, ParsedPlan, StreetEntry

logger = logging.getLogger(__name__)

WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
DAY_RE = re.compile(r"^\d{1,2}$")
CODE_RE = re.compile(r"^([A-T])(?:/([A-T]))?$")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
RANGE_TOKEN_RE = re.compile(r"^(\d+[a-z]?([-–+/]|$)|[-–+]$|Ende$|\+$)", re.IGNORECASE)

# stream index -> waste type slugs served by that calendar/index column
STREAMS = {0: ("restabfall", "bioabfall"), 1: ("papier",), 2: ("gelber-sack",)}
STREAM_LETTERS = {0: set("ABCDEFGHIJ"), 1: set("ABCDEFGHIJKLMNOPQRST"), 2: set("ABCDEFGHIJ")}
# expected collections per tour letter and year (14-day / 4-week rhythm);
# tolerance covers year-boundary effects and holiday irregularities
STREAM_EXPECTED = {0: (23, 28), 1: (10, 15), 2: (23, 28)}


def _row_groups(words, tolerance=2.5):
    rows: dict[int, list[dict]] = {}
    for w in words:
        rows.setdefault(round(w["top"] / tolerance), []).append(w)
    return [sorted(rows[k], key=lambda w: w["x0"]) for k in sorted(rows)]


class LuebeckEblParser(BaseParser):
    key = "luebeck_ebl"

    # ------------------------------------------------------------------
    # entry points
    # ------------------------------------------------------------------
    def parse(self, path: str) -> ParsedPlan:
        return self.parse_multi(path)["gelber-sack"]

    def parse_multi(self, path: str) -> dict[str, ParsedPlan]:
        import pdfplumber

        plans = {slug: ParsedPlan() for slugs in STREAMS.values() for slug in slugs}

        def issue_all(level, code, message):
            for plan in plans.values():
                plan.add_issue(level, code, message)

        with pdfplumber.open(path) as pdf:
            full_text = "\n".join(page.extract_text(x_tolerance=2) or "" for page in pdf.pages)
            year = self._detect_year(full_text)
            if year is None:
                issue_all("error", "year_missing", "Kein Kalenderjahr im Dokument erkannt.")
                return plans
            for plan in plans.values():
                plan.year = year
            issue_all("info", "year_detected", f"Kalenderjahr erkannt: {year}")

            calendar_by_stream, calendar_pages, cal_issues = self._parse_calendar(pdf, year)
            street_rows, street_issues = self._parse_street_index(pdf, calendar_pages)

        for level, code, message in cal_issues + street_issues:
            issue_all(level, code, message)

        # distribute calendar entries and street entries onto the plans
        for stream, slugs in STREAMS.items():
            entries = calendar_by_stream.get(stream, [])
            for slug in slugs:
                plans[slug].calendar = [
                    CalendarEntry(date=d, zone_code=letter, kind=kind, note=note)
                    for d, letter, kind, note in entries
                ]
                plans[slug].streets = self._street_entries_for(street_rows, stream, slug)

        self._validate(plans)
        return plans

    # ------------------------------------------------------------------
    # year detection (§14 – no hard coded year anywhere)
    # ------------------------------------------------------------------
    def _detect_year(self, text: str) -> int | None:
        match = re.search(r"1\.\s*Januar\s+bis\s+31\.\s*Dezember\s+(20\d{2})", text)
        if match:
            return int(match.group(1))
        candidates = [int(y) for y in YEAR_RE.findall(text) if 2000 <= int(y) <= 2100]
        if not candidates:
            return None
        return max(set(candidates), key=candidates.count)

    # ------------------------------------------------------------------
    # calendar spread
    # ------------------------------------------------------------------
    def _parse_calendar(self, pdf, year):
        """Returns ({stream: [(date, letter, kind, note)]}, calendar_pages, issues)."""
        issues = []
        page_results = []
        calendar_pages: set[int] = set()
        for page_no, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(x_tolerance=1.5)
            cells = self._day_cells(words)
            if len(cells) < 150:  # not a calendar page
                continue
            calendar_pages.add(page_no)
            result = self._parse_calendar_page(cells, year, page_no, issues)
            if result:
                page_results.append((page_no, result))

        if not page_results:
            issues.append(("error", "calendar_missing", "Keine Kalenderseite erkannt."))
            return {}, calendar_pages, issues
        issues.append((
            "info", "calendar_pages",
            f"Kalenderseiten erkannt: {', '.join(str(p) for p, _ in page_results)}",
        ))

        # merge the (usually two identical) calendar copies
        merged: dict[tuple, dict[int, str]] = {}
        conflicts = 0
        for _page_no, day_letters in page_results:
            for day, letters in day_letters.items():
                slot = merged.setdefault(day, {})
                for stream, letter in letters.items():
                    if stream in slot and slot[stream] != letter:
                        conflicts += 1
                    else:
                        slot.setdefault(stream, letter)
        if conflicts:
            issues.append((
                "error", "calendar_conflict",
                f"{conflicts} widersprüchliche Zellen zwischen den Kalenderkopien.",
            ))

        by_stream: dict[int, list] = {s: [] for s in STREAMS}
        for (month, day), letters in sorted(merged.items()):
            the_date = date(year, month, day)
            is_saturday = the_date.weekday() == 5
            kind = "shifted" if is_saturday else "regular"
            note = "Ersatztermin (Feiertagsverschiebung)" if is_saturday else ""
            for stream, letter in letters.items():
                by_stream[stream].append((the_date, letter, kind, note))
        return by_stream, calendar_pages, issues

    def _day_cells(self, words):
        """All (day_word, weekday_word, [letter_words]) triples on a page.

        Letters are matched by position (same height, right of the day
        number) instead of by text line: the perforation line of the
        tear-out spread shifts some rows just enough that line grouping
        would lose their letters (observed on every 4th/28th in 2026).
        """
        weekday_words = [w for w in words if w["text"] in WEEKDAYS_DE]
        pairs = []
        for word in words:
            if not DAY_RE.match(word["text"]):
                continue
            partner = None
            for ww in weekday_words:
                if 0 < ww["x0"] - word["x0"] < 25 and abs(ww["top"] - word["top"]) < 5.5:
                    if partner is None or abs(ww["top"] - word["top"]) < abs(partner["top"] - word["top"]):
                        partner = ww
            if partner is not None:
                pairs.append((word, partner))

        code_words = [w for w in words if CODE_RE.match(w["text"])]
        cells = []
        used: set[int] = set()
        for day_w, weekday_w in pairs:
            letters = []
            for idx, lw in enumerate(code_words):
                if idx in used:
                    continue
                if 18 < lw["x0"] - day_w["x0"] < 80 and abs(lw["top"] - day_w["top"]) < 5.5:
                    letters.append((idx, lw))
            letters.sort(key=lambda item: item[1]["x0"])
            used.update(idx for idx, _ in letters)
            cells.append((day_w, weekday_w, [lw for _, lw in letters]))
        return cells

    def _parse_calendar_page(self, cells, year, page_no, issues):
        """One page -> {(month, day): {stream: letter}} with hard validation."""
        # 1. month columns via x-clustering of the day numbers
        xs = sorted(c[0]["x0"] for c in cells)
        columns: list[list[float]] = [[xs[0]]]
        for x in xs[1:]:
            if x - columns[-1][-1] > 30:
                columns.append([])
            columns[-1].append(x)
        if len(columns) != 12:
            issues.append((
                "error", "calendar_columns",
                f"Seite {page_no}: {len(columns)} statt 12 Monatsspalten erkannt.",
            ))
            return None
        bounds = [(min(col) - 5, max(col) + 5) for col in columns]

        def column_of(x):
            for idx, (lo, hi) in enumerate(bounds):
                if lo <= x <= hi:
                    return idx
            return None

        # 2. verify every column against the real calendar (self validation)
        per_month: dict[int, list] = {m: [] for m in range(12)}
        for cell in cells:
            idx = column_of(cell[0]["x0"])
            if idx is not None:
                per_month[idx].append(cell)
        for idx in range(12):
            month = idx + 1
            days_seen = set()
            mismatches = 0
            for day_w, weekday_w, _letters in per_month[idx]:
                day = int(day_w["text"])
                if not 1 <= day <= calendar_mod.monthrange(year, month)[1]:
                    mismatches += 1
                    continue
                days_seen.add(day)
                if WEEKDAYS_DE[date(year, month, day).weekday()] != weekday_w["text"]:
                    mismatches += 1
            expected_days = calendar_mod.monthrange(year, month)[1]
            if mismatches > 1 or len(days_seen) < expected_days - 2:
                issues.append((
                    "error", "calendar_month_invalid",
                    f"Seite {page_no}, Spalte {idx + 1} ({calendar_mod.month_name[month]}): "
                    f"{mismatches} Wochentags-Abweichungen, {len(days_seen)}/{expected_days} Tage.",
                ))
                return None

        # 3. letter slots per column: calibrate from 3-letter cells
        result: dict[tuple, dict[int, str]] = {}
        for idx in range(12):
            month = idx + 1
            slot_samples: dict[int, list[float]] = {0: [], 1: [], 2: []}
            for day_w, _wd, letters in per_month[idx]:
                if len(letters) == 3:
                    for stream, lw in enumerate(letters):
                        slot_samples[stream].append(lw["x0"] - day_w["x0"])
            slots = {
                stream: statistics.median(vals)
                for stream, vals in slot_samples.items()
                if vals
            }
            for day_w, _wd, letters in per_month[idx]:
                if not letters:
                    continue
                day = int(day_w["text"])
                cell: dict[int, str] = {}
                if len(letters) == 3:
                    assignment = enumerate(letters)
                else:
                    if not slots:
                        continue
                    assignment = (
                        (min(slots, key=lambda s: abs(lw["x0"] - day_w["x0"] - slots[s])), lw)
                        for lw in letters
                    )
                for stream, lw in assignment:
                    letter = lw["text"]
                    if letter in STREAM_LETTERS.get(stream, set()) or "/" in letter:
                        cell[stream] = letter
                if cell:
                    result[(month, day)] = cell
        return result

    # ------------------------------------------------------------------
    # street index
    # ------------------------------------------------------------------
    def _parse_street_index(self, pdf, calendar_pages):
        """Returns ([{name, raw_range, codes: (c1, c2, c3), note}], issues)."""
        issues = []
        rows = []
        index_pages = []
        for page_no, page in enumerate(pdf.pages, start=1):
            if page_no in calendar_pages:
                continue
            words = page.extract_words(x_tolerance=2)
            code_words = [w for w in words if CODE_RE.match(w["text"])]
            if len(code_words) < 60:  # index pages carry ~130+ codes
                continue
            page_rows = self._parse_index_page(words, code_words, page_no, issues)
            if page_rows:
                rows.extend(page_rows)
                index_pages.append(page_no)
        if not rows:
            issues.append(("error", "index_missing", "Kein Straßenverzeichnis erkannt."))
        else:
            issues.append((
                "info", "index_pages",
                f"Verzeichnisseiten: {len(index_pages)} (S. {index_pages[0]}–{index_pages[-1]}), "
                f"{len(rows)} Einträge.",
            ))
        return rows, issues

    def _parse_index_page(self, words, code_words, page_no, issues):
        # 1. find the 3-code column triples by clustering code x-positions
        xs = sorted(w["x0"] for w in code_words)
        clusters: list[list[float]] = [[xs[0]]]
        for x in xs[1:]:
            if x - clusters[-1][-1] > 8:
                clusters.append([])
            clusters[-1].append(x)
        centers = [statistics.median(c) for c in clusters if len(c) >= 5]
        if len(centers) % 3 != 0 or not centers:
            issues.append((
                "warning", "index_columns",
                f"Seite {page_no}: {len(centers)} Codespalten (erwartet Vielfaches von 3) – Seite übersprungen.",
            ))
            return []
        triples = [centers[i : i + 3] for i in range(0, len(centers), 3)]

        def code_slot(x):
            for band, triple in enumerate(triples):
                for slot, center in enumerate(triple):
                    if abs(x - center) < 7:
                        return band, slot
            return None

        # layout bands: names start left of their code triple; the left
        # bound must clear the previous code column but stay ahead of the
        # band's name column (observed name offsets vary by ±4pt per page)
        band_bounds = []
        for band, triple in enumerate(triples):
            left = 0 if band == 0 else (triples[band - 1][2] + 10)
            band_bounds.append((left, triple[2] + 12))

        # 2. walk print rows per layout band; entries are BLOCKS: a row whose
        # first band token is a street-name word opens a new entry, rows that
        # start with range tokens or contain only tour codes attach to it.
        # Codes may be sparse (1–3): the three streams split house-number
        # ranges independently (e.g. Kahlhorststraße 2026), and codes of
        # two-line entries sit vertically centred between the text lines.
        entries = []
        for band, (left, right) in enumerate(band_bounds):
            blocks: list[dict] = []
            current: dict | None = None
            for line in _row_groups(words, tolerance=2.2):
                seg = [w for w in line if left <= w["x0"] < right]
                if not seg:
                    continue
                codes: dict[int, str] = {}
                text_tokens: list[str] = []
                for w in seg:
                    slot = code_slot(w["x0"])
                    if slot and slot[0] == band and CODE_RE.match(w["text"]):
                        codes[slot[1]] = w["text"]
                    elif code_slot(w["x0"]) is None:
                        text_tokens.append(w["text"])
                if not codes and not text_tokens:
                    continue
                starts_entry = bool(text_tokens) and not RANGE_TOKEN_RE.match(text_tokens[0])
                if starts_entry or current is None:
                    current = {"name": [], "range": [], "codes": {}}
                    blocks.append(current)
                for token in text_tokens:
                    if RANGE_TOKEN_RE.match(token) or (current["range"] and token in "+-–/"):
                        current["range"].append(token)
                    elif not current["range"]:
                        current["name"].append(token)
                    else:
                        current["range"].append(token)
                for slot, code in codes.items():
                    current["codes"].setdefault(slot, code)
            for state in blocks:
                entry = self._finish_entry(state)
                if entry:
                    entries.append(entry)
        return entries

    def _finish_entry(self, state):
        codes = state["codes"]
        if not codes:
            return None
        name = " ".join(state["name"]).strip()
        raw_range = " ".join(state["range"]).strip()
        if not name or name in {"Straße", "Wegweiser"} or name[0].isdigit():
            return None
        note = ""
        match = re.search(r"\((nur[^)]*)\)", name)
        if match:
            note = match.group(1).strip()
            name = re.sub(r"\s*\(nur[^)]*\)", "", name).strip()
        # single alphabet separator letters between sections ("A", "B", …)
        if len(name) <= 1:
            return None
        return {
            "name": name,
            "raw_range": raw_range,
            "codes": (codes.get(0, ""), codes.get(1, ""), codes.get(2, "")),
            "note": note,
        }

    def _street_entries_for(self, street_rows, stream, slug):
        entries = []
        keywords = {
            "restabfall": ("restabfall", "restmüll"),
            "bioabfall": ("bio",),
            "papier": ("papier",),
            "gelber-sack": ("gelb", "sack"),
        }[slug]
        for row in street_rows:
            code = row["codes"][stream]
            if not code:
                continue
            note = row["note"]
            if note and not any(k in note.lower() for k in keywords):
                # e.g. "(nur Restabfall)": the street stays listed with all
                # three codes, but only the named stream is collected – the
                # other streams get a review note instead of a silent guess.
                note = f"REVIEW: Hinweis im Plan: ({note})"
            elif note:
                note = f"({note})"
            entries.append(
                StreetEntry(
                    name=row["name"],
                    zone_codes=code.split("/"),
                    raw_range=row["raw_range"],
                    note=note,
                )
            )
        return entries

    # ------------------------------------------------------------------
    # validation
    # ------------------------------------------------------------------
    def _validate(self, plans):
        for stream, slugs in STREAMS.items():
            lo, hi = STREAM_EXPECTED[stream]
            expected_letters = STREAM_LETTERS[stream]
            plan = plans[slugs[0]]
            counts = Counter(e.zone_code for e in plan.calendar)
            missing = expected_letters - set(counts)
            if missing:
                for slug in slugs:
                    plans[slug].add_issue(
                        "error", "letters_missing",
                        f"Touren ohne Termine: {', '.join(sorted(missing))}.",
                    )
            for letter, n in sorted(counts.items()):
                if not lo <= n <= hi:
                    for slug in slugs:
                        plans[slug].add_issue(
                            "warning", "letter_count",
                            f"Tour {letter}: {n} Termine (erwartet {lo}–{hi}).",
                        )
            street_count = len(plan.streets)
            if street_count < 1000:
                for slug in slugs:
                    plans[slug].add_issue(
                        "error", "street_count",
                        f"Nur {street_count} Verzeichniseinträge erkannt.",
                    )
