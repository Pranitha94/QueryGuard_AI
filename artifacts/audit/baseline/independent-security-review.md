# Independent security / architecture / evaluation review

Target: 19472ece9771c5530439365d57fe95aa6b176f6a. Main checkout initially clean. All source reviewed directly, without relying on existing audit conclusions. During later verification another worker changed queryguard/providers.py and queryguard/api.py and added tests/test_audit_regressions.py; those edits are not mine and are not approved by this review. Findings below address the original reviewed code/line numbers and initial probe run, not any subsequent remediation.

## Verdict

No reproduced destructive SQL execution, approved-table confidentiality bypass, credential leak or privilege escalation. Several real medium-priority boundary/correctness defects remain in the reviewed revision. Do not inflate these into Internet-critical exploits: the documented boundary is local, single-user and synthetic, and the host administrator/schema owner/model-server configuration is trusted. The default template provider does not expose arbitrary SQL through user questions; SQL findings concern an untrusted/mistaken optional model proposal, exactly the proposed runtime trust boundary.

## Reproduced findings

### 1. Medium: equality-join validation permits a disconnected Cartesian input

Location: queryguard/policy.py:54-62, especially 60. Distinct column aliases are checked, but neither operand must reference the table being introduced by that JOIN. Qualification does not fix the semantic defect.

Minimal SQL:

```sql
SELECT COUNT(*) AS n
FROM analytics.orders o
JOIN analytics.customers c ON o.customer_id=c.customer_id
JOIN analytics.order_items i ON o.customer_id=c.customer_id
```

Actual: accepted, serialized and executed by qg_reader in read-only transaction; result 259200 (360 orders times 720 items), despite the documented no-Cartesian policy. The second join predicate never mentions i. Impact: wrong answers and aggregate intermediate-result amplification from an untrusted model; outer LIMIT 200 does not bound aggregate input. Existing per-statement timeout and four-slot cap remain genuine mitigations; no write/confidentiality bypass demonstrated. Require the ON predicate to connect the newly introduced source to its available input scope, not merely two different alias strings, with nested-scope regression tests.

### 2. Medium: accepted non-finite numeric values cause an uncaught HTTP 500 after an accepted audit event

Locations: queryguard/policy.py:26-28, queryguard/execution.py:23-28, queryguard/api.py:112-134. No JSON-safety/finite-value normalization occurs before recording success and returning the raw result.

Minimal provider proposal:

```sql
SELECT CAST('Infinity' AS DOUBLE PRECISION) AS value
```

Using create_app(provider=synthetic_provider) and TestClient(raise_server_exceptions=False), POST /query returned HTTP 500, body `Internal Server Error`; /history contained status accepted, row_count 1. Actual database execution used qg_reader only. Impact: the documented safe-outcome contract fails, the UI shows transport failure, audit describes acceptance despite failed response delivery. Not a secret leak or data-write exploit. Define a JSON-safe policy for Infinity/NaN/overflowing numeric results before final status/audit serialization; test actual ASGI response serialization, not only run_query().

### 3. Medium hardening gap: 65,536-byte provider response cap is enforced only after full buffering

Location: original queryguard/providers.py:110-118. client.post() eagerly reads the response, and only afterwards checks len(response.content). A synthetic SyncByteStream emitting 128 chunks of 8192 bytes was fully consumed (1,048,576 bytes) before ProviderError. The guard rejects invalid output correctly, but is not a transport memory limit. Impact: oversized or decompression-amplified local server output can use memory beyond the stated cap. Local server configuration is trusted; this is robustness against faulty/untrusted output, not an attacker-controlled remote URL/SSRF claim. Stream incrementally and bound decoded bytes during consumption.

Related observed limitation, not a newly undisclosed bug: timeout is inactivity-based, not a total deadline. A real temporary loopback HTTP server delivered chunks every 0.06s; timeout=0.15 completed successfully in 0.719s. Four slow responses can occupy the four query slots without a wall-clock deadline. SECURITY.md:35 already acknowledges this distinction. The test establishes semantics, not an infinite hang or measured production denial of service.

### 4. Medium hardening gap: question-character limit does not bound the HTTP request body

Locations: queryguard/api.py:24-27, 48, 106-110. Pydantic constrains the decoded question, not bytes buffered/decoded before endpoint execution and slot acquisition. A JSON request with 2,097,152 leading whitespace bytes and a short valid question (2,097,184 total bytes) returned HTTP 200/refused. No sensitive payload or load attack was used. Impact: local clients can induce substantial pre-validation memory/JSON work outside the four query slots. Do not claim this violates the literal 2000-character question rule; it exposes a missing transport budget. Add a streaming ASGI body limit, including chunked/understated Content-Length handling, before JSON parsing. No Internet exposure is assumed.

## Evaluation-integrity findings (not generalization claims)

- Independently reran all 105 committed template cases, schema-aware mode, against the existing synthetic reader connection: 105 passed; 78 expected queries. Separately reran all 40 committed attacks: 40 rejected; no rejected SQL sent to DB. All three fixture SHA-256 values in committed evaluation.json match current questions, attacks and seed. Results are not fabricated by this review.
- Runtime providers do not import answer-key fixtures. Reference execution is separate and read-only; the comparison observes row multiplicity/order, nulls and numeric tolerance. These are meaningful regression controls, not proof of independent held-out design.
- scripts/build_cases.py:25-170 enumerates precisely the provider's supported vocabulary, including loops over months/ranking thresholds. TemplateProvider ignores prompts. Thus 105/105 in two prompt modes is deterministic vocabulary/SQL plumbing coverage, not NL-to-SQL model accuracy, prompt improvement, training/test separation or generalization. Existing README/report disclosures correctly say so.
- Concrete mutation weakness: replace historical item unit_price with current product price in the category-revenue query. The semantically wrong current-price proposal still passes evaluate_cases against the committed reference. sql/seed.sql:28-31 sets every item unit_price=p.price; independent reader query confirmed zero differing item prices. Add price-history variation/semantic mutation testing before stronger SQL-correctness claims. This is a known fixed-fixture limitation, not benchmark cheating.
- Reader query found each customer has 7-8 orders. Therefore five benchmark cases asking for more than 8,9,10,11,12 orders all expect empty results (scripts/build_cases.py:100-107), weakening the apparent hard nested-query coverage. Add nonempty and boundary-discriminating cases rather than counting parameterized records as independent reasoning tasks.
- Numeric comparison uses float conversion and relative tolerance (queryguard/evaluation.py:13-14); acceptable for this documented tiny fixture, but not exact integer/currency identity at large magnitude. Not promoted to a defect of current scores without a failing committed case.

## Architecture / privilege / packaging observations

- Strong separation: provider -> policy -> executor; executor re-reviews forged ReviewedSQL; executable SQL is reserialized AST, not original text. Functions/nodes/types/tables/columns are explicit allowlists, applied before and after qualification. No high-impact escape reproduced.
- verify_runtime checks actual role flags, memberships, database CREATE/TEMP, schema CREATE, table/column write grants and required approved SELECT columns; execution sets read-only and per-statement timeouts. Actual independent probe verified qg_reader and transaction_read_only=on. Extra SELECT grants, schema/table ownership and function/sequence privileges are not comprehensively attested. In the fixed trusted-schema boundary, no reachable exploit was established; do not label these hypothetical paths privilege escalation.
- bootstrap.py is trusted setup code, not an untrusted-input endpoint. External QG_ADMIN_DSN can target an arbitrary server, and bootstrap manages grants/seed there; README warns about this. No bootstrap was run during this audit because it would mutate the demo DB. Existing role passwords/privileges are not fully reconciled on rerun; runtime fail-closed checks mitigate unsafe retained grants. Treat setup preflight/idempotence as operational improvement, not a remote vulnerability.
- Session tokens are metadata-history isolation, explicitly not identity authentication. Anyone local who can reach /sessions can evict existing sessions by creating 100 replacements. This is a consequence of the stated single-user boundary, not missing multi-tenant authorization. Histories/audit are bounded and exclude question/SQL/results/tokens. Audit mkdir/stat/rotation at api.py:123-126 lie outside the sanitized OSError handler at 127-131: certain storage faults return generic 500 instead of promised audit-unavailable 503; low priority and not actively reproduced.
- UI uses plain text/code/dataframe for untrusted question/message/data; static CSS is the only unsafe_allow_html block. CSV neutralization covers headers/cells. No DOM/browser penetration testing performed by this subagent (parent owns browser QA).
- Docker excludes .env/.local/.venv and runs nonroot; Compose separates setup admin credentials from reader runtime, internal DB network, no published DB, loopback API/UI. No container build/run was performed. Images are mutable tags, dependencies pinned without hashes, actions version-tagged; release supply-chain hardening, not a demonstrated compromise. Compose credential interpolation was not inferred from masked terminal output.
- pyproject declares Python >=3.10,<3.13, but committed evidence/CI use 3.10 only. No independent 3.11/3.12 execution or wheel build here. Fresh install audit delegated elsewhere; do not treat this report as clean-room reproducibility verification.
- CI workflow executes bootstrap/lint/format/compile/pytest/evaluation. README's remote CI evidence refers to 59d4c9..., not target HEAD 19472ec; historical success is not independently verified latest-HEAD remote status. This audit did not contact GitHub or rerun remote CI.

## Executed evidence and scope

Created only .local/audit/security/ files: probes.py, results.json, nonfinite.jsonl, body.jsonl, integrity.py, integrity.json, pytest.xml, pytest-temp/, AUDIT.md. Main tracked files were not edited. No admin writes, seed changes, dangerous SQL execution, paid calls or model downloads. Synthetic-only data and temporary synthetic local HTTP server.

Commands:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe .local/audit/security/probes.py
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe .local/audit/security/integrity.py
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_adversarial.py tests/test_security.py tests/test_ollama.py tests/test_evaluation.py tests/test_workspace.py::test_csv_neutralizes_formula_cells_and_headers --junitxml=.local/audit/security/pytest.xml --basetemp=.local/audit/security/pytest-temp
```

Actual targeted regression result: 54 passed in 1.52s. This was not the full suite. Deliberately did not run tests/test_database.py (calls mutating bootstrap), scripts/verify.sh (bootstrap and overwrites release artifacts), scripts/evaluate.py (overwrites release artifacts), live-model or container execution. One FastAPI TestClient import emitted an installed-library deprecation warning in the standalone probe, not a failure.

Authoritative transport references consulted: https://www.python-httpx.org/advanced/timeouts/ (read timeout is maximum wait per response chunk); https://www.python-httpx.org/compatibility/ (streaming/read-all distinction). Current documentation APIs may differ from the installed pinned library; no untested middleware API is prescribed as a verified drop-in fix.

## Hiring assessment / incomplete requirements

Credible junior/early-mid backend or applied-AI systems portfolio: unusually clear trust boundaries, real DB least privilege, typed execution evaluation, measured artifacts, honest simulated-provider labels and actual integration. Not sufficient evidence for senior security engineering, production platform ownership, autonomous-agent safety assurance or LLM/NL-to-SQL research expertise. The AI quality feature remains adapter-level, not empirically demonstrated inference. Fix reproducible safety/serialization boundaries and add discriminating fixtures before calling the requested comprehensive audit complete. Live model generalization, Docker execution, current-HEAD CI, multi-version/fresh packaging, dependency vulnerability audit, wall-clock/body/memory budgets, load tests, static typing and exhaustive grammar review remain unexecuted or incomplete as specified above. Production identity/tenant isolation is intentionally excluded rather than falsely counted as a failed requirement.
