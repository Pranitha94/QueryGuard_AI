# Executed verification — November 26, 2026

Scope: **QueryGuard AI only**, `D:/Hermes/Pranitha_projects/queryguard-ai`. No unrelated project changes, real business/customer data, paid APIs or model downloads. Implementation-stage work was not committed/pushed until parent review and the publication checkpoint below. Native commands used this repository's isolated `.venv/Scripts/python.exe` (Python 3.10.20), not shared `python`/`pip`; remote CI used its fresh Ubuntu Python environment.

## Publication and Linux CI checkpoint

The reviewed implementation (`a6bd6a0`) and parent-run evidence (`59d4c97`) were pushed to `Pranitha94/QueryGuard_AI`. A subsequent `git ls-remote origin refs/heads/main` read matched the full local SHA `59d4c97641cffcf526fb1e3e4d3d4cd8bd812180`.

GitHub Actions run **45850412986** completed with **success** for that SHA. Its job API separately confirmed successful fresh dependency installation on Ubuntu, PostgreSQL service setup and bootstrap, lint, formatting, compilation, pytest, evaluation, and artifact upload. Exact remote status and step outcomes are saved in `artifacts/github-ci.json`. This supersedes the historical unexecuted-CI/Linux-installation notes below. It does **not** verify the full application Docker Compose stack or live LLM inference.

Before this documentation-only publication update, all **38 reviewed executable/configuration files** still matched their approved canonical hashes. No application code changed, so the prior test and review approval is retained without another redundant full local suite. This documentation commit uses `[skip ci]`; the passing CI result is explicitly tied to the tested SHA above.

## Parent-run acceptance checkpoint

After resuming, the parent independently executed `bash scripts/verify.sh`, `.venv/Scripts/python.exe scripts/smoke.py`, `.venv/Scripts/python.exe -m pip check`, `.venv/Scripts/python.exe scripts/record_verification.py`, and shell syntax checks. All commands exited 0.

- Full regression: **65 passed, 1 installed-library deprecation warning, 36.97 seconds**, no failures or skips.
- Lint, formatting (25 files), compilation, dependency consistency, and shell syntax passed.
- Both **SIMULATED/TEMPLATE** evaluation settings: **105/105** correct outcomes, comprising **78/78** execution-equivalent queries and **27/27** clarification/refusal outcomes; **40/40** adversarial SQL cases rejected.
- Baseline mean/p95 latency: **120.715 / 223.225 ms**; schema-aware: **119.664 / 221.658 ms**. These are template-demo timings, not live-model quality or prompt-improvement evidence.
- Live API/UI smoke: four expected query outcomes, isolated history, live schema, evaluation HTTP 200, and UI health HTTP 200.
- Evidence was regenerated from these real executions; local-secret scan reported zero matches. The JUnit hostname was removed by the evidence helper.
- Independent source/security review **passed** for the documented local synthetic demo, with no blocking security or logic findings. The reviewer inspected all 53 text files in the 55-path snapshot, including all 25 Python files, and independently rejected all 40 captured attacks. The parent visually inspected both screenshots. Nonblocking hardening recommendations are recorded in `artifacts/code-review.json`. Nothing had been committed or pushed at this checkpoint.

The implementation-stage results below are retained as historical evidence. The latest machine-readable results are in `artifacts/`.

## Implementation-stage acceptance results (historical)

`bash scripts/verify.sh` completed successfully:

- Idempotent PostgreSQL bootstrap: 48 customers, 12 products, 360 orders, 720 order items.
- Ruff lint: **All checks passed**. Final formatter check: **25 files already formatted** (including the evidence-recording helper).
- `python -m compileall -q queryguard scripts workspace.py`: exit 0.
- `python -m pytest -q --tb=short --junitxml=artifacts/pytest.xml`: final regression **65 passed, 1 warning, 18.05 seconds**, no skips/failures/errors. This followed the successful 64-test `verify.sh` gate (30.31 seconds) and one final UI privacy RED/GREEN slice. The warning is installed Starlette's deprecation of its httpx-backed TestClient, not a test failure. No dependency replacement was attempted merely to silence it.
- Evaluator completed both prompt settings and the adversarial corpus with no failures/skips.

|Executed template setting|All outcomes correct|SQL valid|Execution-equivalent references|Clarification/refusal correct|Mean end-to-end ms|p95 ms|
|---|---:|---:|---:|---:|---:|---:|
|baseline|105/105|78/78 queries|78/78 queries|27/27|135.992|245.367|
|schema-aware|105/105|78/78 queries|78/78 queries|27/27|132.999|243.967|

**SIMULATED/TEMPLATE only.** These are measured results for the documented vocabulary, not held-out NL-to-SQL model accuracy. The template ignores prompt text, so there is no measured prompt improvement. Nonquery records comprise 12 clarifications and 15 refusals. Latency includes schema introspection, generation/policy and execution, excludes independent reference execution, and varies by machine/load; it is not a production performance benchmark.

**40/40 distinct SQL attacks rejected** by executed policy calls, no skips. Rejected SQL was never sent to PostgreSQL. Actual database privilege denials are tested separately, with default read-only mode explicitly disabled before CREATE/TEMP/UPDATE/role-escalation attempts. This distinction matters: an AST rejection is not evidence of executing an unsafe statement or a proof of complete security.

References were independently authored without calling/importing the provider, then actually executed through a separate read-only PostgreSQL path on the same seed. Comparison checks typed values, nulls, row multiplicity and ordering when specified; numeric relative/absolute tolerance is 1e-6. A regression with a deliberately wrong 361 reference versus actual 360 proves the evaluator detects disagreement rather than trusting answer keys. Every per-case SQL/result/outcome is in the actual JSON artifact; fixture SHA-256 values tie the report to the committed seed/questions/attacks.

## Baseline and incremental RED → GREEN record

The initial combined tool invocation timed out without yielding a test baseline. Re-running the explicit test command produced **10 failures, 2 passes in 17.63s**. Existing work was retained and repaired/extended, not replaced with an unrelated scaffold.

|Slice / exact test command prefix: `.venv/Scripts/python.exe -m pytest`|Observed RED|Observed GREEN|
|---|---|---|
|`tests/test_ollama.py -q` (included in original `-q` baseline)|Missing `OllamaProvider`: success + five invalid/timeout scenarios failed|Adapter added; complete existing suite **12 passed in 1.89s** after DB workaround|
|`tests/test_api.py -q`|Missing `queryguard.api`, **1 failed**|Real-DB session/query/schema/history slice **1 passed**|
|`tests/test_adversarial.py -q`|40 attacks passed rejection; powerful runtime DSN test **failed: DID NOT RAISE**|Per-connection runtime-role verification added; adversarial + API subset **42 passed**|
|`tests/test_evaluation.py -q`|Missing evaluator module, **1 failed**|Typed comparison **1 passed**|
|`tests/test_evaluation.py -q` (second vertical slice)|Missing executed `evaluate_cases`, **1 failed, 1 passed**|Independent wrong-reference check **2 passed**|
|`tests/test_adversarial.py::test_supported_boolean_date_filters_execute -q`|Valid date filter rejected: SQLGlot `And` is also an `exp.Func`|Narrow `And`/`Or` function-node allowlist correction: **1 passed**, then both benchmark settings **105/105**|
|`tests/test_workspace.py -q`|Missing presentation helper and workspace, **2 failed**|CSV/chart selection and Streamlit AppTest rendering **2 passed**|
|`tests/test_adversarial.py::test_parser_never_logs_untrusted_sql -q`|Parser warning echoed synthetic sensitive marker, **1 failed**|Suppressed SQLGlot warning records; API/privacy/workspace subset **5 passed**|
|`tests/test_workspace.py::test_workspace_renders_questions_and_provider_messages_as_plain_text -q --tb=short`|Untrusted question/provider Markdown reached rendered Markdown, **1 failed**|Plain-text rendering blocks external-image/link interpretation: **1 passed**, final full regression **65 passed**|

The first full evaluator run was **75/105** per setting, not silently called a success. Its 30 rejected valid cases identified the boolean-node compatibility bug. A minimal date-filter regression established RED, then the policy fix made it GREEN before the full evaluator rerun.

Additional preserved-work coverage validates actual ACL denials, row caps (200/1/0), smaller-limit preservation, record uniqueness/counts, no runtime benchmark-reference imports, bounded/clearable history, provider/execution errors, sanitized validation and three audit outcomes. `tests/test_limits.py -q --tb=short`: **3 passed**. Final complete suite result is the 65-test gate above; targeted passing subsets are not substituted for it.

## Live services and browser evidence

The native PostgreSQL instance originally suffered child-process startup failures with Windows exception `0xC0000142`. Its underlying Windows cause was **not established**. A dedicated persistent/foreground server process succeeded and remained healthy; no other database/services were stopped or modified.

Executed persistent DB command:

```bash
'C:/Program Files/PostgreSQL/16/bin/postgres.exe' -D D:/Hermes/Pranitha_projects/queryguard-ai/.local/pgdata
```

Observed live settings: PostgreSQL **16.11**, `listen_addresses=127.0.0.1`, port **55432**, reader `default_transaction_read_only=on`, `statement_timeout=2s`. Verified separately that actual ACLs still deny writes when READ WRITE is selected.

Executed API and UI commands:

```bash
.venv/Scripts/python.exe -m uvicorn queryguard.api:app --host 127.0.0.1 --port 8000 --no-access-log
.venv/Scripts/python.exe -m streamlit run workspace.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false --server.headless true
# API was subsequently restarted successfully through the supplied script:
bash scripts/run_api.sh
.venv/Scripts/python.exe scripts/smoke.py
```

Smoke output: **4 expected query outcomes, isolated history, live schema, evaluation 200, UI health 200**. Actual requests: category revenue accepted; monthly revenue accepted; underspecified revenue clarified; password request refused. Synthetic response SQL, rows and timings are recorded in `artifacts/http-smoke.json`, without session tokens.

- API: `http://127.0.0.1:8000`; OpenAPI: `/docs`.
- Workspace: `http://127.0.0.1:8501`; health endpoint `/_stcore/health` returned 200.
- Real browser clicked **Run example** and observed accepted SQL, chart, table and safe CSV download control. Actual category totals displayed: Electronics 24975, Home 22365, Office 19755.
- Browser opened the live Evaluation lab, displaying actual report counters/timings and explicit simulated-provider labeling.
- Screenshots: `docs/screenshots/analytics.png` and `docs/screenshots/evaluation.png`. They are real browser captures, not generated mockups. Initial contrast mismatch was corrected using the committed Streamlit dark theme.

## Other executed checks

```bash
.venv/Scripts/python.exe -m ruff check queryguard scripts tests workspace.py
.venv/Scripts/python.exe -m ruff format --check queryguard scripts tests workspace.py
.venv/Scripts/python.exe -m compileall -q queryguard scripts workspace.py
bash -n scripts/run_api.sh scripts/run_ui.sh scripts/verify.sh
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe scripts/record_verification.py
```

Lint/format/compile/shell syntax checks passed. `pip check`: **No broken requirements found.** The evidence helper scanned publishable project text for actual local DSNs/passwords without printing them; zero matches. It removes JUnit's irrelevant host identity attribute while preserving all actual outcomes/timings. No `.env`, `.venv`, `.local`, raw logs or secrets are intended for publication.

Docker state was rechecked instead of relying on the stale initial brief: daemon **29.6.1** was reachable. Compose configuration was actually validated with synthetic, nonsecret environment values:

```bash
QG_ADMIN_PASSWORD=synthetic_compose_validation_only QG_READER_PASSWORD=synthetic_reader_validation_only docker compose --env-file .env.example config --quiet
```

Configuration passed. `docker image inspect postgres:16.11 python:3.10-slim --format '{{.RepoTags}}'` reported both required base images absent. No large image/dependency downloads, container build or container run were undertaken. Docker execution remains **unverified**, not blocked by an unavailable daemon. GitHub Actions files exist but no remote workflow was run or published.

## Evidence index

|Path|What it proves|
|---|---|
|`artifacts/pytest.xml`|Executed 65-test outcomes/timings, no skips/failures/errors|
|`artifacts/evaluation.json`|Both settings, per-case actual/reference typed rows/SQL, counters, timings, fixture hashes and attack outcomes|
|`artifacts/EVALUATION.md`|Readable actual report and methodology/limitations|
|`artifacts/http-smoke.json`|Actual HTTP query outcomes, schema/history isolation and API/UI readiness|
|`artifacts/verification.json`|Nonsecret live environment, parsed test/eval summaries, Compose status and local-secret scan|
|`benchmarks/questions.json`|105 inspectable question/reference/status records with ordering/difficulty/category|
|`benchmarks/adversarial.json`|40 distinct inspectable attack SQL records|
|`docs/screenshots/`|Actual browser evidence|

## Limits and unresolved verification

No live Ollama inference/model download, Docker container execution, clean-room/Linux dependency installation, published CI run, static type check, load test, vulnerability audit, exhaustive SQL fuzzing, production auth/tenant isolation or independent penetration test. Six Ollama cases use honest HTTP doubles. No Gemini adapter was added. See `SECURITY.md` for residual risks, including administrator-controlled PostgreSQL logs and process-local history/audit limitations.

Online primary-reference fetches were attempted for the brief's Ollama structured-output docs, PostgreSQL 16 client settings and SQLGlot qualifier source. Extraction was blocked by the fetcher's network-address policy; the alternate real-browser Ollama fetch timed out. Those pages were not represented as successfully consulted; implementation behavior was checked against installed APIs and executed tests instead. Reference pointers for later review:

- `https://docs.ollama.com/capabilities/structured-outputs`
- `https://www.postgresql.org/docs/16/runtime-config-client.html`
- `https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/qualify.py`

The runnable native end-to-end scope is verified. This is not a claim of complete security, production deployment or actual LLM quality.
