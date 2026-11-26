import importlib.util


def test_template_query_is_explicitly_simulated():
    assert importlib.util.find_spec("queryguard.providers"), "structured provider is missing"
    from queryguard.db import inspect_schema
    from queryguard.providers import TemplateProvider, build_prompt, retrieve_schema

    schema = inspect_schema()
    selected = retrieve_schema("Show revenue by region.", schema)
    assert set(selected["tables"]) == {"customers", "orders", "order_items", "products"}
    prompt = build_prompt("Show revenue by region.", selected, "schema-aware")
    assert "UNTRUSTED" in prompt and "row samples" in prompt
    result = TemplateProvider().generate("Show revenue by region.", prompt)
    assert result.status == "query" and "JOIN" in result.sql
    assert TemplateProvider.label == "SIMULATED / TEMPLATE (not an LLM)"
