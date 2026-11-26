import json

import httpx
import pytest

import queryguard.providers as providers


def test_ollama_schema_contract_success():
    assert hasattr(providers, "OllamaProvider"), "Ollama structured adapter missing"

    def handler(request):
        body = json.loads(request.content)
        assert body["stream"] is False and body["format"]["type"] == "object"
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": '{"status":"query","sql":"SELECT COUNT(*) AS n FROM analytics.orders"}'
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        p = providers.OllamaProvider(client=client, model="test-double")
        assert p.generate("count", "prompt").status == "query"


@pytest.mark.parametrize("kind", ["timeout", "invalid_json", "extra_field", "inconsistent", "server_error"])
def test_ollama_failure_has_no_template_fallback(kind):
    assert hasattr(providers, "OllamaProvider"), "Ollama structured adapter missing"

    def handler(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("synthetic test timeout")
        contents = {
            "invalid_json": "not json",
            "extra_field": '{"status":"refused","surprise":true}',
            "inconsistent": '{"status":"refused","sql":"DELETE FROM orders"}',
        }
        return httpx.Response(
            503 if kind == "server_error" else 200, json={"message": {"content": contents.get(kind, "")}}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(providers.ProviderError, match="structured response"):
            providers.OllamaProvider(client=client, model="test-double").generate(
                "How many orders are there?", "prompt"
            )
