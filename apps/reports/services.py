"""Export helpers shared by the analytics dashboard and admin (§18)."""

import csv
import io


def rows_to_csv(headers: list[str], rows: list[list]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel opens UTF-8 correctly
