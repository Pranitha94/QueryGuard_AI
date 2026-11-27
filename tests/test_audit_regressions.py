"""Regressions for independently reproduced audit findings; no live LLM required."""

import httpx
import pytest

from queryguard.providers import OllamaProvider, ProviderError


def test_policy_rejects_join_predicate_that_omits_new_alias():
    from queryguard.policy import PolicyError, review_sql

    sql = (
        "SELECT COUNT(*) FROM analytics.orders o "
        "JOIN analytics.customers c ON o.customer_id=c.customer_id "
        "JOIN analytics.order_items i ON o.customer_id=c.customer_id"
    )
    with pytest.raises(PolicyError, match="newly joined"):
        review_sql(sql)


@pytest.mark.parametrize(
    "expression",
    ["CAST('Infinity' AS DOUBLE PRECISION)", "CAST('NaN' AS NUMERIC)", "CAST('1e10000' AS NUMERIC)"],
)
def test_api_unserializable_numeric_result_is_not_audited_as_success(tmp_path, expression):
    from fastapi.testclient import TestClient

    from queryguard.api import create_app
    from queryguard.providers import Proposal

    class NonfiniteProvider:
        label = "SYNTHETIC NUMERIC DOUBLE"

        def generate(self, question, prompt):
            return Proposal(status="query", sql=f"SELECT {expression} AS value")

    with TestClient(
        create_app(provider=NonfiniteProvider(), audit_path=tmp_path / "audit.jsonl"),
        raise_server_exceptions=False,
    ) as client:
        headers = {"X-Session-Token": client.post("/sessions").json()["token"]}
        response = client.post("/query", headers=headers, json={"question": "numeric boundary"})
        assert response.status_code == 200
        assert response.json()["status"] == "execution_error"
        assert response.json()["rows"] == []
        assert client.get("/history", headers=headers).json()["items"][0]["status"] == "execution_error"


@pytest.mark.parametrize("chunked", [False, True])
def test_api_rejects_oversized_body_before_provider(tmp_path, chunked):
    from fastapi.testclient import TestClient

    from queryguard.api import create_app
    from queryguard.providers import Proposal

    calls = []

    class CountingProvider:
        label = "SYNTHETIC BODY BUDGET DOUBLE"

        def generate(self, question, prompt):
            calls.append(question)
            return Proposal(status="refused", message="synthetic")

    with TestClient(create_app(provider=CountingProvider(), audit_path=tmp_path / "audit.jsonl")) as client:
        headers = {
            "X-Session-Token": client.post("/sessions").json()["token"],
            "Content-Type": "application/json",
        }
        body = b" " * 20000 + b'{"question":"unsupported"}'
        content = iter([body[:10000], body[10000:]]) if chunked else body
        response = client.post("/query", headers=headers, content=content)
        assert response.status_code == 413
        assert response.json() == {"detail": "Request body exceeds 16384 bytes."}
        assert calls == []


def test_evaluation_detects_current_price_instead_of_historical_item_price():
    import json

    from queryguard.db import ROOT
    from queryguard.evaluation import evaluate_cases
    from queryguard.providers import TemplateProvider

    case = next(
        c
        for c in json.loads((ROOT / "benchmarks/questions.json").read_text())
        if c["question"].lower() == "show revenue by category"
    )

    class WrongPriceProvider(TemplateProvider):
        def generate(self, question, prompt):
            proposal = super().generate(question, prompt)
            return proposal.model_copy(update={"sql": proposal.sql.replace("i.unit_price", "p.price")})

    result = evaluate_cases([case], WrongPriceProvider(), "schema-aware")
    assert result[0]["passed"] is False, "Seed failed to distinguish historical from current prices"


def test_evaluation_detects_inclusive_instead_of_strict_order_threshold():
    import json

    from queryguard.db import ROOT
    from queryguard.evaluation import evaluate_cases
    from queryguard.providers import TemplateProvider

    case = next(
        c
        for c in json.loads((ROOT / "benchmarks/questions.json").read_text())
        if c["question"].lower() == "show customers with more than 6 orders"
    )

    class WrongBoundaryProvider(TemplateProvider):
        def generate(self, question, prompt):
            proposal = super().generate(question, prompt)
            return proposal.model_copy(update={"sql": proposal.sql.replace(">6", ">=6")})

    result = evaluate_cases([case], WrongBoundaryProvider(), "schema-aware")
    assert result[0]["passed"] is False, "Seed failed to distinguish a strict threshold from inclusive"


def test_workspace_live_provider_does_not_show_template_banner(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from queryguard.db import ROOT

    original = httpx.Client

    def handler(request):
        fixtures = {
            "/health": {"provider": "OLLAMA / LIVE (synthetic configuration double)"},
            "/sessions": {"token": "synthetic-live-label-session"},
            "/schema": {"tables": {}, "relationships": []},
            "/history": {"items": []},
        }
        if request.url.path in fixtures:
            return httpx.Response(200, json=fixtures[request.url.path])
        return httpx.Response(404)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    app = AppTest.from_file(str(ROOT / "workspace.py")).run(timeout=30)
    assert not app.exception
    assert not any(c.value.startswith("TEMPLATE DEMO:") for c in app.caption)
    assert any("OLLAMA ADAPTER:" in c.value for c in app.caption)


def test_supported_runtime_uses_fixed_pillow_release():
    from importlib.metadata import version

    from packaging.version import Version

    assert Version(version("pillow")) >= Version("13.0.0"), "Pillow advisories require fixed release"


def test_ollama_stops_reading_at_response_byte_budget():
    observed = {"tail_consumed": False, "closed": False}

    class OversizedStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 65537
            observed["tail_consumed"] = True
            yield b"more untrusted data"

        def close(self):
            observed["closed"] = True

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=OversizedStream()))
    ) as client:
        with pytest.raises(ProviderError):
            OllamaProvider(model="synthetic-test-double", client=client).generate("count", "prompt")
    assert observed["tail_consumed"] is False, "Oversized provider output was buffered beyond its budget"
    assert observed["closed"] is True


@pytest.mark.parametrize("failure", ["directory", "rotation"])
def test_audit_filesystem_failures_return_sanitized_unavailable(tmp_path, failure):
    from fastapi.testclient import TestClient

    from queryguard.api import create_app

    if failure == "directory":
        parent = tmp_path / "blocked"
        parent.write_text("synthetic blocker")
        audit_path = parent / "audit.jsonl"
    else:
        audit_path = tmp_path / "audit.jsonl"
        audit_path.write_text("x" * 1_000_001)
        audit_path.with_suffix(".previous.jsonl").mkdir()
    with TestClient(create_app(audit_path=audit_path), raise_server_exceptions=False) as client:
        headers = {"X-Session-Token": client.post("/sessions").json()["token"]}
        for _ in range(5):
            response = client.post("/query", headers=headers, json={"question": "Show revenue"})
            assert response.status_code == 503
            assert response.json() == {"detail": "Audit unavailable."}
        assert client.get("/history", headers=headers).json()["items"] == []


def test_workspace_renews_expired_session_once_without_crashing(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from queryguard.db import ROOT

    original = httpx.Client
    issued = []

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"provider": "SIMULATED AUDIT DOUBLE"})
        if request.url.path == "/sessions":
            issued.append("new-synthetic-session")
            return httpx.Response(201, json={"token": issued[-1]})
        if request.headers.get("X-Session-Token") != "new-synthetic-session":
            return httpx.Response(401, json={"detail": "Session expired"})
        if request.url.path == "/schema":
            return httpx.Response(200, json={"tables": {}, "relationships": []})
        if request.url.path == "/history":
            return httpx.Response(200, json={"items": []})
        return httpx.Response(404)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    app = AppTest.from_file(str(ROOT / "workspace.py"))
    app.session_state.token = "expired-synthetic-session"
    app.run(timeout=20)
    assert not app.exception
    assert app.session_state.token == "new-synthetic-session"
    assert len(issued) == 1


def test_workspace_clear_history_failure_is_displayed_without_traceback(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from queryguard.db import ROOT

    original = httpx.Client

    def handler(request):
        if request.method == "DELETE":
            return httpx.Response(503, json={"detail": "Synthetic service unavailable"})
        fixtures = {
            "/health": {"provider": "SIMULATED AUDIT DOUBLE"},
            "/schema": {"tables": {}, "relationships": []},
            "/history": {"items": []},
        }
        if request.url.path in fixtures:
            return httpx.Response(200, json=fixtures[request.url.path])
        return httpx.Response(404)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    app = AppTest.from_file(str(ROOT / "workspace.py"))
    app.session_state.token = "synthetic-ui-session"
    app.run(timeout=20)
    next(b for b in app.button if b.label == "Clear session history").click().run(timeout=20)
    assert not app.exception
    assert any("could not be cleared" in error.value for error in app.error)


def test_api_expires_and_evicts_old_sessions(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import queryguard.api as api

    clock = [100.0]
    monkeypatch.setattr(api, "monotonic", lambda: clock[0])
    with TestClient(api.create_app(audit_path=tmp_path / "audit.jsonl")) as client:
        token = client.post("/sessions").json()["token"]
        headers = {"X-Session-Token": token}
        assert client.get("/history", headers=headers).status_code == 200
        clock[0] += 3601
        assert client.get("/history", headers=headers).status_code == 401
        oldest = client.post("/sessions").json()["token"]
        newest = oldest
        for _ in range(100):
            newest = client.post("/sessions").json()["token"]
        assert client.get("/history", headers={"X-Session-Token": oldest}).status_code == 401
        assert client.get("/history", headers={"X-Session-Token": newest}).status_code == 200


def test_api_audit_rotation_preserves_bounded_previous_file(tmp_path):
    import json

    from fastapi.testclient import TestClient

    from queryguard.api import create_app

    audit = tmp_path / "audit.jsonl"
    audit.write_text("x" * 1_000_001)
    with TestClient(create_app(audit_path=audit)) as client:
        headers = {"X-Session-Token": client.post("/sessions").json()["token"]}
        result = client.post("/query", headers=headers, json={"question": "Show revenue"})
        assert result.status_code == 200
        assert result.json()["status"] == "clarification"
    assert audit.with_suffix(".previous.jsonl").stat().st_size == 1_000_001
    event = json.loads(audit.read_text())
    assert event["status"] == "clarification"
    assert "question" not in event and "sql" not in event


def test_api_rejects_concurrency_over_capacity_and_releases_slots(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock

    from fastapi.testclient import TestClient

    from queryguard.api import create_app
    from queryguard.providers import Proposal

    started, release, lock = Event(), Event(), Lock()
    state = {"active": 0}

    class BlockingProvider:
        label = "SYNTHETIC CONCURRENCY DOUBLE"

        def generate(self, question, prompt):
            with lock:
                state["active"] += 1
                if state["active"] == 4:
                    started.set()
            if not release.wait(15):
                raise RuntimeError("Synthetic test release timed out")
            return Proposal(status="refused", message="Synthetic bounded test")

    with TestClient(create_app(provider=BlockingProvider(), audit_path=tmp_path / "audit.jsonl")) as client:
        headers = {"X-Session-Token": client.post("/sessions").json()["token"]}

        def send():
            return client.post("/query", headers=headers, json={"question": "test capacity"})

        with ThreadPoolExecutor(max_workers=4) as pool:
            pending = [pool.submit(send) for _ in range(4)]
            try:
                assert started.wait(10), "Four calls did not reach the synthetic provider"
                assert send().status_code == 429
            finally:
                release.set()
            assert all(f.result(timeout=10).status_code == 200 for f in pending)
        assert send().status_code == 200
