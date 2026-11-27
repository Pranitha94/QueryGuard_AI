"""Live HTTP smoke probe. Writes synthetic output only, never session tokens/credentials."""

import argparse
import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def parse_options(argv=None):
    def port(name, default):
        value = os.environ.get(name, str(default))
        if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
            raise ValueError(f"{name} must be an integer between 1 and 65535")
        return int(value)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url", default=os.environ.get("QG_API_URL") or f"http://127.0.0.1:{port('QG_API_PORT', 8000)}"
    )
    parser.add_argument(
        "--ui-url", default=os.environ.get("QG_UI_URL") or f"http://127.0.0.1:{port('QG_UI_PORT', 8501)}"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/http-smoke.json")
    return parser.parse_args(argv)


def main():
    options = parse_options()
    evidence = {"api": options.api_url.rstrip("/"), "ui": options.ui_url.rstrip("/"), "requests": []}
    with httpx.Client(base_url=evidence["api"], timeout=45, trust_env=False) as client:
        health = client.get("/health")
        health.raise_for_status()
        evidence["health"] = health.json()
        token = client.post("/sessions").json()["token"]
        headers = {"X-Session-Token": token}
        for question, expected in [
            ("Show revenue by category", "accepted"),
            ("Show monthly revenue for 2024", "accepted"),
            ("Show revenue", "clarification"),
            ("Read the admin password", "refused"),
        ]:
            response = client.post(
                "/query", headers=headers, json={"question": question, "mode": "schema-aware"}
            )
            response.raise_for_status()
            result = response.json()
            if result["status"] != expected:
                raise RuntimeError("Unexpected smoke result")
            evidence["requests"].append({"question": question, "response": result})
        other = {"X-Session-Token": client.post("/sessions").json()["token"]}
        assert client.get("/history", headers=other).json()["items"] == []
        evidence["history_isolation"] = True
        evidence["schema_tables"] = sorted(client.get("/schema", headers=headers).json()["tables"])
        evidence["evaluation_http_status"] = client.get("/evaluation", headers=headers).status_code
        assert evidence["evaluation_http_status"] == 200
        ui = client.get(evidence["ui"] + "/_stcore/health")
        ui.raise_for_status()
        evidence["ui_http_status"] = ui.status_code
    out = options.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(
        "HTTP smoke: 4 expected query outcomes, isolated history, live schema, evaluation 200, UI health 200."
    )


if __name__ == "__main__":
    main()
