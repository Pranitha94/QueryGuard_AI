from queryguard.db import connect, verify_runtime
from queryguard.policy import MAX_ROWS, ReviewedSQL, review_sql


class ExecutionError(RuntimeError):
    pass


def execute(reviewed: ReviewedSQL):
    # Even a caller-constructed ReviewedSQL cannot bypass policy.
    safe = review_sql(reviewed.sql)
    try:
        with connect() as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout = '2000ms'")
            conn.execute("SET LOCAL lock_timeout = '500ms'")
            conn.execute("SET LOCAL search_path = analytics, pg_catalog")
            verify_runtime(conn)
            with conn.cursor() as cursor:
                cursor.execute(safe.sql)
                columns = [c.name for c in cursor.description]
                rows = cursor.fetchmany(MAX_ROWS)
        return {
            "sql": safe.sql,
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
        }
    except Exception:
        raise ExecutionError("Query could not be completed safely") from None
