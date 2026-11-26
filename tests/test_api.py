import importlib.util


def test_query_session_and_history_use_real_database():
    assert importlib.util.find_spec("queryguard.api"), "FastAPI service missing"
    from fastapi.testclient import TestClient

    from queryguard.api import create_app

    with TestClient(create_app()) as client:
        assert client.get("/health").json()["database"] == "ready"
        assert client.get("/history").status_code == 401
        token = client.post("/sessions").json()["token"]
        headers = {"X-Session-Token": token}
        response = client.post(
            "/query", headers=headers, json={"question": "How many orders are there?", "mode": "schema-aware"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "accepted" and body["rows"] == [[360]]
        assert "SIMULATED" in body["provider"]
        assert body["summary"] == "Returned 1 row and 1 column."
        history = client.get("/history", headers=headers).json()["items"]
        assert len(history) == 1 and "question" not in history[0] and "rows" not in history[0]
        other = {"X-Session-Token": client.post("/sessions").json()["token"]}
        assert client.get("/history", headers=other).json()["items"] == []
        assert client.post("/query", headers=headers, json={"question": "x" * 2001}).status_code == 422
        assert client.get("/schema", headers=headers).json()["source"].startswith("live PostgreSQL")


def test_rejection_provider_and_execution_errors_are_sanitized_and_audited(tmp_path):
    from fastapi.testclient import TestClient

    from queryguard.api import create_app
    from queryguard.providers import Proposal, ProviderError

    class SyntheticProvider:
        label = "SYNTHETIC TEST DOUBLE"

        def generate(self, question, prompt):
            if question == "provider-error":
                raise ProviderError("synthetic-sensitive-marker")
            if question == "sql-attack":
                return Proposal(status="query", sql="SELECT pg_sleep(10)")
            return Proposal(status="query", sql="SELECT 1/0 AS result")

    audit = tmp_path / "audit.jsonl"
    with TestClient(create_app(provider=SyntheticProvider(), audit_path=audit)) as client:
        h = {"X-Session-Token": client.post("/sessions").json()["token"]}
        for question, status in [
            ("provider-error", "provider_error"),
            ("sql-attack", "rejected"),
            ("division", "execution_error"),
        ]:
            response = client.post("/query", headers=h, json={"question": question})
            assert response.status_code == 200 and response.json()["status"] == status
            assert "synthetic-sensitive-marker" not in response.text
        invalid = client.post(
            "/query", headers=h, json={"question": "synthetic-sensitive-marker", "surprise": True}
        )
        assert invalid.status_code == 422 and "synthetic-sensitive-marker" not in invalid.text
        events = audit.read_text()
        assert len(events.splitlines()) == 3
        for excluded in [
            "synthetic-sensitive-marker",
            "pg_sleep",
            "division",
            "question",
            "sql",
            "rows",
            h["X-Session-Token"],
        ]:
            assert excluded not in events
