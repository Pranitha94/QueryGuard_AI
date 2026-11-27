import importlib.util


def test_csv_neutralizes_formula_cells_and_headers():
    assert importlib.util.find_spec("queryguard.presentation"), "Workspace presentation helpers missing"
    from queryguard.presentation import chart_kind, csv_bytes

    content = csv_bytes(["=header", "value"], [[" +cmd", 5], ["@attack", None], ["safe", "\t=1"]]).decode(
        "utf-8-sig"
    )
    assert "'=header" in content and "' +cmd" in content and "'@attack" in content and "'\t=1" in content
    assert chart_kind(["month", "revenue"], [["2024-01-01", 12], ["2024-02-01", 18]]) == "line"
    assert chart_kind(["region", "revenue"], [["North", 12], ["South", 18]]) == "bar"
    assert chart_kind(["total"], [[360]]) == "metric"


def test_streamlit_renders_without_errors(monkeypatch):
    """Deterministic component render; real API/database journeys run separately."""
    import httpx
    from streamlit.testing.v1 import AppTest

    from queryguard.db import ROOT

    original = httpx.Client

    def handler(request):
        fixtures = {
            "/health": {"provider": "SIMULATED COMPONENT TEST DOUBLE"},
            "/sessions": {"token": "synthetic-render-session"},
            "/schema": {"tables": {}, "relationships": []},
            "/history": {"items": []},
        }
        return (
            httpx.Response(200, json=fixtures[request.url.path])
            if request.url.path in fixtures
            else httpx.Response(404)
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    app = AppTest.from_file(str(ROOT / "workspace.py")).run(timeout=30)
    assert not app.exception
    assert any("QueryGuard" in title.value for title in app.title)
    assert len(app.tabs) == 4


def test_evaluation_summary_is_accessible_plain_table(monkeypatch):
    import json

    import httpx
    from streamlit.testing.v1 import AppTest

    from queryguard.db import ROOT

    original = httpx.Client
    saved = json.loads((ROOT / "artifacts/evaluation.json").read_text())
    report = {**saved, "runs": [{"mode": r["mode"], "summary": r["summary"]} for r in saved["runs"]]}

    def handler(request):
        fixtures = {
            "/health": {"provider": "SIMULATED TABLE COMPONENT DOUBLE"},
            "/sessions": {"token": "synthetic-table-session"},
            "/schema": {"tables": {}, "relationships": []},
            "/history": {"items": []},
            "/evaluation": report,
        }
        return httpx.Response(200, json=fixtures[request.url.path])

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    app = AppTest.from_file(str(ROOT / "workspace.py")).run(timeout=30)
    assert not app.exception
    assert len(app.table) == 1, "Two-row evaluation should not depend on an offscreen canvas grid"
    values = app.table[0].value
    assert list(values["Passed / total"]) == [
        f"{r['summary']['passed']} / {r['summary']['total']}" for r in report["runs"]
    ]


def test_workspace_renders_questions_and_provider_messages_as_plain_text(monkeypatch):
    import httpx
    from streamlit.testing.v1 import AppTest

    from queryguard.db import ROOT

    original_client = httpx.Client

    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"provider": "SIMULATED UI TEST DOUBLE"})
        if request.url.path == "/schema":
            return httpx.Response(200, json={"tables": {}, "relationships": []})
        if request.url.path == "/history":
            return httpx.Response(200, json={"items": []})
        return httpx.Response(404)

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs)
    )
    marker = "![synthetic-external-image](https://example.invalid/sensitive-marker)"
    app = AppTest.from_file(str(ROOT / "workspace.py"))
    app.session_state.token = "synthetic-ui-token"
    app.session_state.messages = [
        {
            "question": marker,
            "result": {"status": "refused", "message": marker, "latency_ms": 0, "row_count": 0},
        }
    ]
    app.run(timeout=30)
    assert not app.exception
    assert not any("sensitive-marker" in item.value for item in app.markdown)
    assert sum("sensitive-marker" in item.value for item in app.text) == 2
