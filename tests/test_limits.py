import json

from queryguard.execution import execute
from queryguard.policy import review_sql


def test_row_ceiling_preserves_smaller_limits():
    for requested, expected in [(99999, 200), (1, 1), (0, 0)]:
        result = execute(
            review_sql(f"SELECT order_id FROM analytics.orders ORDER BY order_id LIMIT {requested}")
        )
        assert result["row_count"] == expected
    assert execute(review_sql("SELECT order_id FROM analytics.orders"))["row_count"] == 200


def test_committed_fixture_counts_and_independence():
    from queryguard.db import ROOT
    from tests.test_adversarial import ATTACKS

    questions = json.loads((ROOT / "benchmarks/questions.json").read_text())
    attacks = json.loads((ROOT / "benchmarks/adversarial.json").read_text())
    assert len(questions) >= 100 and len({q["id"] for q in questions}) == len(questions)
    assert len(attacks) >= 30 and len({a["sql"] for a in attacks}) == len(attacks)
    assert [(a["id"], a["sql"]) for a in attacks] == ATTACKS
    for filename in ["providers.py", "service.py"]:
        source = (ROOT / "queryguard" / filename).read_text()
        assert "benchmarks/" not in source and "reference_sql" not in source


def test_history_bounds_and_clear(tmp_path):
    from fastapi.testclient import TestClient

    from queryguard.api import create_app

    with TestClient(create_app(audit_path=tmp_path / "audit.jsonl")) as client:
        headers = {"X-Session-Token": client.post("/sessions").json()["token"]}
        for _ in range(52):
            result = client.post(
                "/query", headers=headers, json={"question": "unsupported synthetic question"}
            )
            assert result.json()["status"] == "refused"
        assert len(client.get("/history", headers=headers).json()["items"]) == 50
        assert client.delete("/history", headers=headers).json()["cleared"] is True
        assert client.get("/history", headers=headers).json()["items"] == []
