import pytest

from queryguard.policy import PolicyError, review_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT c.customer_id FROM customers c CROSS JOIN orders o",
        "SELECT 1 FROM orders o JOIN customers c ON TRUE",
    ],
)
def test_unbounded_cartesian_join_is_rejected(sql):
    with pytest.raises(PolicyError, match="Join requires"):
        review_sql(sql)
