import pytest

from queryguard.policy import PolicyError, review_sql

ATTACKS = [
    ("stacked", "SELECT 1; DELETE FROM analytics.orders"),
    ("delete", "DELETE FROM analytics.orders"),
    (
        "update_cte",
        "WITH x AS (UPDATE analytics.orders SET status='pending' RETURNING order_id) SELECT order_id FROM x",
    ),
    (
        "insert_cte",
        "WITH x AS (INSERT INTO analytics.products VALUES (99,'x','Home',1) RETURNING product_id) SELECT product_id FROM x",
    ),
    ("drop", "DROP TABLE analytics.orders"),
    ("select_into", "SELECT order_id INTO analytics.stolen FROM analytics.orders"),
    ("lock", "SELECT order_id FROM analytics.orders FOR UPDATE"),
    ("catalog", "SELECT rolname FROM pg_catalog.pg_roles"),
    ("information_schema", "SELECT table_name FROM information_schema.tables"),
    ("public_schema", "SELECT order_id FROM public.orders"),
    ("database_qualifier", "SELECT order_id FROM otherdb.analytics.orders"),
    ("sleep", "SELECT pg_sleep(20)"),
    ("file_read", "SELECT pg_read_file('/etc/passwd')"),
    ("config", "SELECT set_config('search_path','public',false)"),
    ("dblink", "SELECT dblink_connect('host=evil')"),
    ("generate_series", "SELECT x FROM generate_series(1,1000000000) x"),
    ("recursive", "WITH RECURSIVE r AS (SELECT 1 AS n UNION ALL SELECT n+1 FROM r) SELECT n FROM r"),
    ("star", "SELECT * FROM analytics.customers"),
    ("qualified_star", "SELECT c.* FROM analytics.customers c"),
    ("unknown_column", "SELECT password FROM analytics.customers"),
    ("cte_unknown", "WITH c AS (SELECT password FROM analytics.customers) SELECT password FROM c"),
    (
        "nested_catalog",
        "SELECT customer_id FROM analytics.customers WHERE EXISTS (SELECT 1 FROM pg_catalog.pg_roles)",
    ),
    (
        "union_catalog",
        "SELECT customer_label FROM analytics.customers UNION SELECT rolname FROM pg_catalog.pg_roles",
    ),
    ("cast_regclass", "SELECT 'pg_authid'::regclass"),
    ("cast_custom", "SELECT 'x'::public.evil"),
    ("copy", "COPY analytics.customers TO '/tmp/leak'"),
    ("explain", "EXPLAIN ANALYZE SELECT order_id FROM analytics.orders"),
    ("negative_limit", "SELECT order_id FROM analytics.orders LIMIT -1"),
    ("expression_limit", "SELECT order_id FROM analytics.orders LIMIT (SELECT 1)"),
    ("cross_join", "SELECT c.customer_id FROM analytics.customers c CROSS JOIN analytics.orders o"),
    ("constant_join", "SELECT o.order_id FROM analytics.orders o JOIN analytics.customers c ON TRUE"),
    ("lateral", "SELECT c.customer_id FROM analytics.customers c, LATERAL (SELECT 1) x"),
    ("window", "SELECT ROW_NUMBER() OVER () FROM analytics.orders"),
    ("distinct_on", "SELECT DISTINCT ON (status) status FROM analytics.orders"),
    ("quoted_trick", 'SELECT "password;drop" FROM analytics.customers'),
    ("unauthorized_function", "SELECT current_setting('data_directory')"),
    ("comment_function", "SELECT pg_/*comment*/sleep(10)"),
    ("offset", "SELECT order_id FROM analytics.orders OFFSET 1000000"),
    ("huge_literal", "SELECT '" + "x" * 1001 + "'"),
    ("complex_expression", "SELECT " + "+".join(["1"] * 160)),
]


@pytest.mark.parametrize("name,sql", ATTACKS, ids=[x[0] for x in ATTACKS])
def test_adversarial_rejection(name, sql):
    with pytest.raises(PolicyError):
        review_sql(sql)


def test_parser_never_logs_untrusted_sql(caplog):
    import logging

    secret = "synthetic-sensitive-marker"
    with caplog.at_level(logging.WARNING, logger="sqlglot"):
        with pytest.raises(PolicyError):
            review_sql("EXPLAIN ANALYZE SELECT " + repr(secret))
    assert secret not in caplog.text


def test_supported_boolean_date_filters_execute():
    from queryguard.execution import execute

    result = execute(
        review_sql(
            "SELECT order_id FROM analytics.orders WHERE order_date >= DATE '2024-01-01' AND order_date < DATE '2024-02-01' ORDER BY order_id"
        )
    )
    assert result["row_count"] > 0


def test_execute_refuses_powerful_runtime(monkeypatch):
    import os

    from dotenv import dotenv_values

    from queryguard.db import ROOT
    from queryguard.execution import ExecutionError, execute

    monkeypatch.setenv(
        "QG_DATABASE_DSN", os.environ.get("QG_ADMIN_DSN") or dotenv_values(ROOT / ".env")["QG_ADMIN_DSN"]
    )
    with pytest.raises(ExecutionError, match="safely"):
        execute(review_sql("SELECT COUNT(*) FROM analytics.orders"))
