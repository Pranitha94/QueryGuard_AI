import importlib.util


def test_reviewed_select_executes_with_bound():
    assert importlib.util.find_spec("queryguard.policy"), "AST review module is missing"
    from queryguard.execution import execute
    from queryguard.policy import review_sql

    result = execute(
        review_sql("SELECT customer_id, region FROM analytics.customers ORDER BY customer_id LIMIT 99999")
    )
    assert len(result["rows"]) == 48
    assert result["columns"] == ["customer_id", "region"]
    assert "99999" not in result["sql"]
