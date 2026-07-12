"""Parser for the official Lübeck "Gelber Sack" PDF.

Structure of the document (analysed 2026 edition, documented in
docs/ANALYSE.md):

* Page 1 contains general information and the year calendar. The calendar
  itself is embedded as a raster image, therefore it is read via OCR
  (RapidOCR, pip-only – no system dependency).
* Page 2 contains the street list ("Straße" / "Bezirk" columns) as real,
  extractable text with positional information.

The parser never writes to the database – it returns a ParsedPlan that the
import service validates and applies (§15).
"""

import calendar as calendar_mod
import io
import logging
import re
import statistics
from datetime import date

from .base import BaseParser, CalendarEntry, ParsedPlan, StreetEntry

logger = logging.getLogger(__name__)

MONTHS = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
MONTH_ALIASES = {"Mär": 3, "Marz": 3, "März": 3}
WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

ZONE_CODE_RE = re.compile(r"^([A-J])(?:/([A-J]))?$")
# OCR confusions for zone letters, applied only inside the Bezirk column
OCR_LETTER_FIXES = {"1": "I", "l": "I", "|": "I", "i": "I", "J.": "J", "0": "D"}
OCR_LETTER_CLASS = r"[A-J1l|i]"
MERGED_WEEKDAY_ZONE_RE = re.compile(rf"^(Mo|Di|Mi|Do|Fr|Sa|So)\.?\s+({OCR_LETTER_CLASS})$")
MERGED_FULL_RE = re.compile(rf"^(\d{{1,2}})\s+(Mo|Di|Mi|Do|Fr|Sa|So)\.?\s+({OCR_LETTER_CLASS})$")

YEAR_RE = re.compile(r"\b(20\d{2})\b")


class LuebeckGelberSackParser(BaseParser):
    key = "luebeck_gelber_sack"

    # ------------------------------------------------------------------
    # entry point
    # ------------------------------------------------------------------
    def parse(self, path: str) -> ParsedPlan:
        import pdfplumber

        plan = ParsedPlan()
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) < 2:
                plan.add_issue("warning", "page_count", f"Erwartet 2 Seiten, gefunden: {len(pdf.pages)}")
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            plan.year = self._detect_year(full_text, plan)
            self._parse_streets(pdf, plan)

        self._parse_calendar_ocr(path, plan)
        self._validate_calendar(plan)
        return plan

    # ------------------------------------------------------------------
    # year detection (§14 – no hard coded year anywhere)
    # ------------------------------------------------------------------
    def _detect_year(self, text: str, plan: ParsedPlan) -> int | None:
        candidates = [int(y) for y in YEAR_RE.findall(text)]
        candidates = [y for y in candidates if 2000 <= y <= 2100]
        if not candidates:
            plan.add_issue("error", "year_missing", "Kein Kalenderjahr im Dokument erkannt.")
            return None
        # The plan year is the most frequent plausible year in the document.
        year = max(set(candidates), key=candidates.count)
        plan.add_issue("info", "year_detected", f"Kalenderjahr erkannt: {year}")
        return year

    # ------------------------------------------------------------------
    # street list (text based, page 2)
    # ------------------------------------------------------------------
    def _parse_streets(self, pdf, plan: ParsedPlan) -> None:
        page = pdf.pages[-1]
        # x_tolerance=6 merges letter-spaced street names ("K a h l h o r s t")
        # while the gap to the Bezirk column stays far larger.
        words = page.extract_words(keep_blank_chars=False, x_tolerance=6)
        if not words:
            plan.add_issue("error", "streets_no_text", "Straßenliste enthält keinen extrahierbaren Text.")
            return

        bezirk_columns = [
            (w["x0"] + w["x1"]) / 2 for w in words if w["text"] == "Bezirk"
        ]
        if len(bezirk_columns) < 4:
            plan.add_issue(
                "error", "streets_layout",
                f"Spaltenüberschriften nicht erkannt ({len(bezirk_columns)} „Bezirk“-Spalten).",
            )
            return

        def near_bezirk_column(x_center: float) -> bool:
            return any(abs(x_center - col) < 18 for col in bezirk_columns)

        # group words into visual lines
        lines: dict[int, list[dict]] = {}
        for word in words:
            key = round(word["top"] / 4)
            lines.setdefault(key, []).append(word)

        header_tokens = {"Straße", "Bezirk", "Stadt Lübeck", "Stadt", "Lübeck", "Abfuhrbezirke"}
        entries: list[tuple[str, str]] = []

        for key in sorted(lines):
            line = sorted(lines[key], key=lambda w: w["x0"])
            name_tokens: list[str] = []
            for word in line:
                text = word["text"].strip()
                if text in header_tokens:
                    continue
                x_center = (word["x0"] + word["x1"]) / 2
                if ZONE_CODE_RE.match(text) and near_bezirk_column(x_center):
                    name = self._clean_street_name(" ".join(name_tokens))
                    if name:
                        entries.append((name, text))
                    name_tokens = []
                else:
                    name_tokens.append(text)

        if len(entries) < 100:
            plan.add_issue(
                "error", "streets_too_few",
                f"Nur {len(entries)} Straßeneinträge erkannt – Layout vermutlich geändert.",
            )
            return

        for raw_name, code in entries:
            entry = self._build_street_entry(raw_name, code)
            if entry:
                plan.streets.append(entry)

        plan.add_issue("info", "streets_parsed", f"{len(plan.streets)} Straßeneinträge erkannt.")

    @staticmethod
    def _clean_street_name(raw: str) -> str:
        # remove alphabetical section markers such as "- A -"
        value = re.sub(r"-\s*[A-ZÄÖÜ]\s*-", " ", raw)
        value = re.sub(r"\s+", " ", value).strip(" -")
        return value.strip()

    def _build_street_entry(self, raw_name: str, code: str) -> StreetEntry | None:
        match = ZONE_CODE_RE.match(code)
        zone_codes = [match.group(1)]
        if match.group(2):
            zone_codes.append(match.group(2))

        district = ""
        district_match = re.search(r"\(([^)]+)\)", raw_name)
        if district_match:
            district = district_match.group(1).strip()
            raw_name = raw_name.replace(district_match.group(0), "").strip()

        # split off house number range information (e.g. "1-32/43", "34/45-Ende")
        raw_range = ""
        range_match = re.search(r"\s(\d[\d\w/.\- ]*(?:Ende|ab)?|ab .*|bis .*)$", raw_name)
        if range_match and any(ch.isdigit() for ch in range_match.group(1)):
            raw_range = range_match.group(1).strip()
            raw_name = raw_name[: range_match.start()].strip()

        name = raw_name.strip(" ,-")
        if len(name) < 3:
            return None
        return StreetEntry(name=name, district=district, zone_codes=zone_codes, raw_range=raw_range)

    # ------------------------------------------------------------------
    # calendar (OCR based, page 1 – the calendar is a raster image)
    # ------------------------------------------------------------------
    def _extract_calendar_image(self, path: str):
        """Return the embedded calendar image as PIL image, or None."""
        import pypdfium2 as pdfium
        import pypdfium2.raw as pdfium_raw

        pdf = pdfium.PdfDocument(path)
        try:
            best = None
            for obj in pdf[0].get_objects():
                if obj.type == pdfium_raw.FPDF_PAGEOBJ_IMAGE:
                    image = obj.get_bitmap(render=False).to_pil()
                    if best is None or image.size[0] > best.size[0]:
                        best = image
        finally:
            pdf.close()
        if best is not None and best.size[0] >= 1200:
            return best
        return None

    def _parse_calendar_ocr(self, path: str, plan: ParsedPlan) -> None:
        if plan.year is None:
            return
        image = self._extract_calendar_image(path)
        if image is None:
            plan.add_issue(
                "error", "calendar_no_image",
                "Kalendergrafik nicht gefunden – manuelle Erfassung oder Community-Fallback nötig (§24).",
            )
            return

        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            plan.add_issue(
                "error", "ocr_unavailable",
                "OCR-Abhängigkeit (rapidocr-onnxruntime) ist nicht installiert.",
            )
            return

        # 2x upscaling improves detection of small glyphs considerably.
        scale = 2
        image = image.convert("RGB").resize((image.size[0] * scale, image.size[1] * scale))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        ocr = RapidOCR()
        raw_results, _ = ocr(buffer.getvalue())
        if not raw_results:
            plan.add_issue("error", "ocr_empty", "OCR lieferte kein Ergebnis für die Kalendergrafik.")
            return

        tokens = []
        for box, text, confidence in raw_results:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            tokens.append(
                {
                    "text": text.strip(),
                    "x": sum(xs) / len(xs) / scale,
                    "y": sum(ys) / len(ys) / scale,
                    "conf": float(confidence),
                }
            )

        self._tokens_to_calendar(tokens, plan, image=image, scale=scale, ocr=ocr)

    def _tokens_to_calendar(
        self, tokens: list[dict], plan: ParsedPlan, image=None, scale: int = 1, ocr=None
    ) -> None:
        """Geometry based cell mapping.

        The month names are printed red-on-yellow and are unreliable for OCR,
        so the twelve month columns are derived from the x positions of the
        day-number tokens instead (12 tight clusters, ~183px pitch). Rows are
        evenly spaced; a least squares fit maps y positions to day numbers.
        """
        year = plan.year

        # 1) month columns: cluster the x positions of day-number tokens
        day_tokens = [
            t for t in tokens
            if re.fullmatch(r"[1-9]|[12]\d|3[01]", t["text"]) and t["conf"] > 0.8
        ]
        columns = self._cluster_columns([t["x"] for t in day_tokens])
        if len(columns) != 12:
            plan.add_issue(
                "error", "calendar_columns",
                f"{len(columns)} statt 12 Monatsspalten erkannt – Kalenderlayout vermutlich geändert.",
            )
            return
        pitch = statistics.median(b - a for a, b in zip(columns, columns[1:], strict=False))

        def column_month(x: float, max_offset_left: float = 20) -> int | None:
            for month_no, col_x in enumerate(columns, start=1):
                if col_x - max_offset_left <= x < col_x + pitch * 0.9:
                    return month_no
            return None

        # 2) day rows: least squares fit y = slope * day + intercept
        per_day: dict[int, list[float]] = {}
        for token in day_tokens:
            per_day.setdefault(int(token["text"]), []).append(token["y"])
        points = [(day, statistics.median(ys)) for day, ys in per_day.items()]
        if len(points) < 20:
            plan.add_issue("error", "calendar_rows", "Tageszeilen im Kalender nicht erkennbar.")
            return
        n = len(points)
        sum_d = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_dd = sum(p[0] ** 2 for p in points)
        sum_dy = sum(p[0] * p[1] for p in points)
        slope = (n * sum_dy - sum_d * sum_y) / (n * sum_dd - sum_d**2)
        intercept = (sum_y - slope * sum_d) / n

        def row_day(y: float) -> int:
            return round((y - intercept) / slope)

        # 3) zone letters: single letters in the Bezirk sub-column
        #    (~+85..+165px right of the day-number column) plus merged tokens
        seen: dict[tuple[int, int], CalendarEntry] = {}

        def add_entry(month_no: int, day: int, letter: str, note: str = "") -> None:
            _, days_in_month = calendar_mod.monthrange(year, month_no)
            if not 1 <= day <= days_in_month:
                return
            entry_date = date(year, month_no, day)
            kind = "shifted" if entry_date.weekday() >= 5 or note else "regular"
            if entry_date.weekday() >= 5 and not note:
                note = "Ersatztermin (Feiertagsverschiebung)"
            seen[(month_no, day)] = CalendarEntry(
                date=entry_date, zone_code=letter, kind=kind, note=note
            )

        for token in tokens:
            text = token["text"].strip()
            month_no = column_month(token["x"], max_offset_left=30)
            if month_no is None:
                continue
            offset = token["x"] - columns[month_no - 1]

            merged_full = MERGED_FULL_RE.fullmatch(text)
            if merged_full:
                letter = OCR_LETTER_FIXES.get(merged_full.group(3), merged_full.group(3))
                add_entry(month_no, int(merged_full.group(1)), letter)
                continue
            merged = MERGED_WEEKDAY_ZONE_RE.fullmatch(text)
            if merged:
                letter = OCR_LETTER_FIXES.get(merged.group(2), merged.group(2))
                add_entry(month_no, row_day(token["y"]), letter)
                continue

            letter = OCR_LETTER_FIXES.get(text, text)
            if re.fullmatch(r"[A-J]", letter) and pitch * 0.35 < offset < pitch * 0.95:
                add_entry(month_no, row_day(token["y"]), letter)

        # 4) recovery pass: the OCR *detector* misses very thin glyphs (the
        #    free-standing zone letter "I"). All grid cells without a letter
        #    are cropped and classified recognition-only.
        if image is not None and ocr is not None:
            recovered = self._recover_missing_letters(
                image, scale, ocr, columns, pitch, slope, intercept, seen, add_entry, year
            )
            if recovered:
                plan.add_issue(
                    "info", "calendar_recovered",
                    f"{recovered} Termine im Zellen-Zweitpass ergänzt.",
                )

        plan.calendar = sorted(seen.values(), key=lambda e: e.date)
        plan.add_issue("info", "calendar_parsed", f"{len(plan.calendar)} Abfuhrtermine per OCR erkannt.")

    def _recover_missing_letters(
        self, image, scale, ocr, columns, pitch, slope, intercept, seen, add_entry, year
    ) -> int:
        """Crop empty letter cells and run recognition-only OCR on them."""
        import numpy as np

        gray = np.array(image.convert("L"))
        rgb = np.array(image)
        recovered = 0
        for month_no, col_x in enumerate(columns, start=1):
            _, days_in_month = calendar_mod.monthrange(year, month_no)
            for day in range(1, days_in_month + 1):
                if (month_no, day) in seen:
                    continue
                # Recovery only targets regular weekdays; weekend replacement
                # dates carry highlighted merged tokens the main pass catches.
                if date(year, month_no, day).weekday() >= 5:
                    continue
                y_center = (intercept + slope * day) * scale
                # tight window around the expected letter position, excluding
                # the vertical grid lines left and right of the sub-column
                x0 = int((col_x + pitch * 0.50) * scale)
                x1 = int((col_x + pitch * 0.78) * scale)
                y0 = int(y_center - slope * scale * 0.40)
                y1 = int(y_center + slope * scale * 0.40)
                if y0 < 0 or y1 > gray.shape[0] or x1 > gray.shape[1]:
                    continue
                if (gray[y0:y1, x0:x1] < 128).sum() < 60:  # cell is effectively empty
                    continue
                letter = ""
                result, _ = ocr(rgb[y0:y1, x0:x1], use_det=False, use_cls=False)
                if result:
                    first = result[0]
                    text = str(first[0] if isinstance(first, list | tuple) else first).strip()
                    score = (
                        float(first[1]) if isinstance(first, list | tuple) and len(first) > 1 else 0.0
                    )
                    text = re.sub(r"[^A-Za-z0-9|]", "", text)
                    candidate = OCR_LETTER_FIXES.get(text, text)
                    if re.fullmatch(r"[A-J]", candidate) and score >= 0.5:
                        letter = candidate
                if not letter and self._looks_like_letter_i(gray[y0:y1, x0:x1]):
                    letter = "I"
                if letter:
                    add_entry(month_no, day, letter)
                    recovered += 1
        return recovered

    @staticmethod
    def _looks_like_letter_i(cell) -> bool:
        """Detect the letter "I" that OCR systematically misses.

        A free-standing "I" is a single narrow, tall, border-free connected
        component; grid line fragments always touch the crop border and note
        text produces wide components.
        """
        import cv2
        import numpy as np

        binary = (cell < 128).astype(np.uint8)
        count, _, stats, _ = cv2.connectedComponentsWithStats(binary)
        height, width = cell.shape
        candidates = []
        for i in range(1, count):
            _x, _y, w, h, area = stats[i]
            if area < 15:
                continue
            if w <= 3 and h >= height * 0.9:  # vertical grid line fragment
                continue
            if h <= 3 and w >= width * 0.9:  # horizontal grid line fragment
                continue
            candidates.append((int(w), int(h), int(area)))
        if len(candidates) != 1:
            return False
        w, h, area = candidates[0]
        return 5 <= w <= 14 and h >= 2.2 * w and h <= height * 0.95 and area >= 0.5 * w * h

    @staticmethod
    def _cluster_columns(xs: list[float], gap: float = 60) -> list[float]:
        """Cluster x positions into column centers (sorted left to right)."""
        clusters: list[list[float]] = []
        for x in sorted(xs):
            if clusters and x - clusters[-1][-1] < gap:
                clusters[-1].append(x)
            else:
                clusters.append([x])
        return [statistics.median(cluster) for cluster in clusters]

    # ------------------------------------------------------------------
    # parser level plausibility validation (§32)
    # ------------------------------------------------------------------
    def _validate_calendar(self, plan: ParsedPlan) -> None:
        if not plan.calendar:
            return
        per_zone: dict[str, list[date]] = {}
        for entry in plan.calendar:
            per_zone.setdefault(entry.zone_code, []).append(entry.date)

        for zone, dates in sorted(per_zone.items()):
            dates.sort()
            if len(dates) < 20 or len(dates) > 32:
                plan.add_issue(
                    "warning", "zone_count",
                    f"Bezirk {zone}: ungewöhnliche Terminanzahl ({len(dates)}) – bitte prüfen.",
                )
            gaps = [(b - a).days for a, b in zip(dates, dates[1:], strict=False)]
            odd_gaps = [g for g in gaps if not 6 <= g <= 22]
            if odd_gaps:
                plan.add_issue(
                    "warning", "zone_rhythm",
                    f"Bezirk {zone}: unplausible Abstände {odd_gaps} – bitte prüfen.",
                )
