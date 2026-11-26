"""Result-only presentation; no model conjecture or unescaped HTML."""

import csv
import io
from datetime import date
from numbers import Number


def csv_bytes(columns, rows):
    def neutralize(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        if isinstance(value, str) and value.startswith(("\t", "\r", "\n")):
            return "'" + value
        return value

    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([neutralize(c) for c in columns])
    writer.writerows([[neutralize(v) for v in row] for row in rows])
    return stream.getvalue().encode("utf-8-sig")


def chart_kind(columns, rows):
    if len(columns) == 1 and len(rows) == 1 and isinstance(rows[0][0], Number):
        return "metric"
    if (
        len(columns) != 2
        or not rows
        or not all(isinstance(row[1], Number) and not isinstance(row[1], bool) for row in rows)
    ):
        return "table"
    try:
        for row in rows:
            date.fromisoformat(str(row[0])[:10])
        return "line"
    except (ValueError, TypeError):
        return "bar" if len(rows) <= 30 else "table"
