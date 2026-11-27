# Verified feature list — QueryGuard AI

**Scope:** a local single-user analytics demonstration over synthetic PostgreSQL data. The default provider is explicitly SIMULATED/TEMPLATE. Test counts, timings, platforms and final acceptance status are centralized in `TEST_RESULTS.md`; do not treat a historical artifact as a fresh execution.

|Implemented capability|Evidence and verification boundary|
|---|---|
|Synthetic customers, products, orders and order items, with primary/foreign keys and seeded relationships|`sql/seed.sql`, database integration tests; actual PostgreSQL, not an in-memory substitute|
|Separate setup credential and restricted runtime reader, column SELECT grants, no write/create/temp capabilities|`scripts/bootstrap.py`, `queryguard/db.py`, `tests/test_database.py`; negative privilege operations are actually attempted against the dedicated synthetic database|
|Live allowlisted schema introspection without row samples|`queryguard/db.py::inspect_schema`, `/schema`, real browser Schema explorer journey|
|Deterministic documented question families producing executable SQL|`queryguard/providers.py::TemplateProvider`, provider tests, independent reference execution; **not real model inference**|
|Modular Ollama structured JSON adapter and no silent template fallback|`tests/test_ollama.py`; HTTP doubles for success, timeout, malformed JSON and inconsistent output; no live-model claim|
|Provider response byte budget during receipt, with response closure and compressed-output rejection|`test_ollama_stops_reading_at_response_byte_budget`; demonstrated early stop rather than checking only after full buffering|
|One read-only SQL statement with explicit node/function/type/table/column authorization|`queryguard/policy.py`, adversarial corpus and tests; checks nested ASTs, name resolution and the reserialized executable statement|
|Join predicates must connect the introduced alias to an earlier source|`test_policy_rejects_join_predicate_that_omits_new_alias`; closes a reproduced disconnected-input amplification case; not proof of business-relationship correctness|
|Bounded rows, AST size/depth, equality joins, statement/lock timeouts and restricted search path|Policy/execution tests and actual PostgreSQL operations; row cap is not a total workload bound|
|Executor rechecks even caller-constructed reviewed SQL and rejects privileged runtime connections|`queryguard/execution.py`, `test_execute_refuses_powerful_runtime`|
|Explicit accepted, clarification, refused, rejected, provider_error and execution_error outcomes|Service/API tests and real accepted/clarification/refusal browser journeys|
|Nonfinite and oversized numeric JSON failures produce a safe error before a false accepted audit event|`test_api_unserializable_numeric_result_is_not_audited_as_success`; Infinity, NaN and extreme numeric results actually come from PostgreSQL|
|A POST request body budget before JSON decoding/provider execution|`queryguard/request_limits.py`, fixed and streamed request-body regression cases; not a full HTTP denial-of-service defense|
|Opaque expiring sessions, bounded/isolated history, eviction and clear behavior|API integration tests, expiry/eviction coverage and real browser clear-history journey; **not identity authentication**|
|Concurrency ceiling and slot recovery after failures|`test_api_rejects_concurrency_over_capacity_and_releases_slots`, audit-failure tests; controlled overlapping requests with an explicit blocking provider double|
|Data-minimal audit append/rotation and sanitized filesystem failures|Audit tests verify directory/rotation failures, bounded previous file and absence of raw query data; not a durable compliance ledger|
|Expired UI session renewal and safe history-clear error rendering|Streamlit component tests with explicit HTTP doubles; no uncaught traceback on the covered error paths|
|Provider-aware UI labels and plain-text rendering of untrusted content|UI regression tests for configured Ollama versus simulation and Markdown/image payloads; configuration is not successful inference|
|Analytics workspace with reviewed SQL, tables, simple charts and actual CSV download|Live browser journey evidence in `artifacts/audit/browser-journeys.json`; CSV was actually downloaded and parsed|
|Formula-neutralized CSV headers and cells|`test_csv_neutralizes_formula_cells_and_headers`; not a guarantee about every spreadsheet configuration|
|Schema, evaluation and session-history tabs; empty state; desktop/mobile rendering and keyboard focus|Recorded browser assertions/screenshots; no exhaustive accessibility claim|
|Independent reference execution with typed/order-aware/multiset result comparison|`queryguard/evaluation.py`, evaluator mismatch tests, actual per-case records in `artifacts/evaluation.json`|
|Discriminating historical-price and strict-threshold fixtures|Seed v2 and two mutation regressions; semantically wrong current-price/inclusive-threshold proposals no longer pass those covered cases|
|Inspectable question and adversarial corpora with explicit simulated labels and actual results|`benchmarks/`, `artifacts/EVALUATION.md`; scores are template regression results, not held-out LLM accuracy|
|Reproducibility helpers, dependency pins, Docker/CI recipes and audit documentation|See the exact tested reproduction/package/CI scope in `AUDIT_REPORT.md` and `TEST_RESULTS.md`; authored configuration alone is not an executed deployment|

## Not counted as implemented-and-verified features

Live LLM quality, general natural-language understanding, real-user login, tenant authorization, durable conversation memory, rich SQL narration, production deployment, a full load/security/accessibility certification, client experience and business impact. None is inferred from project screenshots or a green unit-test count.
