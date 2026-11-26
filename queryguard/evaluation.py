"""Typed comparison for independently executed reference results (not SQL string match)."""

import math
from datetime import date, datetime
from decimal import Decimal


def cell_equal(a, b):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float, Decimal)) and isinstance(b, (int, float, Decimal)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(a, (date, datetime)) or isinstance(b, (date, datetime)):
        return type(a) is type(b) and a == b
    return type(a) is type(b) and a == b


def same_results(actual, expected, ordered=False):
    if len(actual) != len(expected):
        return False

    def row_equal(a, b):
        return len(a) == len(b) and all(cell_equal(x, y) for x, y in zip(a, b, strict=True))

    if ordered:
        return all(row_equal(a, b) for a, b in zip(actual, expected, strict=True))
    # Maximum bipartite matching preserves multiplicity even with numeric tolerance.
    matches = {}

    def augment(i, visited):
        for j, row in enumerate(expected):
            if j not in visited and row_equal(actual[i], row):
                visited.add(j)
                if j not in matches or augment(matches[j], visited):
                    matches[j] = i
                    return True
        return False

    return all(augment(i, set()) for i in range(len(actual)))


def evaluate_cases(cases, provider, mode):
    from queryguard.db import connect, verify_runtime
    from queryguard.service import run_query

    records = []
    for case in cases:
        expected = None
        # References deliberately bypass the model and SQL policy, not the DB privilege boundary.
        # They are committed trusted fixtures executed independently on the same synthetic DB.
        if case["reference_sql"]:
            with connect() as conn:
                conn.execute("SET TRANSACTION READ ONLY")
                conn.execute("SET LOCAL statement_timeout='2000ms'")
                verify_runtime(conn)
                cursor = conn.execute(case["reference_sql"])
                expected = cursor.fetchmany(201)
                if len(expected) > 200:
                    raise ValueError("Reference result exceeds documented comparison cap")
        actual = run_query(case["question"], mode, provider)
        status_ok = actual["status"] == case["expected_status"]
        passed = status_ok and (expected is None or same_results(actual["rows"], expected, case["ordered"]))
        records.append(
            {
                "id": case["id"],
                "question": case["question"],
                "expected_status": case["expected_status"],
                "actual_status": actual["status"],
                "passed": passed,
                "sql_valid": actual["status"] == "accepted",
                "actual_sql": actual["sql"],
                "reference_sql": case["reference_sql"],
                "latency_ms": actual["latency_ms"],
                "ordered": case["ordered"],
                "actual_rows": typed_rows(actual["rows"]),
                "reference_rows": typed_rows(expected) if expected is not None else None,
            }
        )
    return records


def typed_rows(rows):
    return [
        [{"type": type(v).__name__, "value": str(v) if v is not None else None} for v in row] for row in rows
    ]
