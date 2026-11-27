# Actual test and evaluation results — QueryGuard AI audit

## Provenance and scope

Audit base: `19472ece9771c5530439365d57fe95aa6b176f6a`. Native candidate: Windows 11, isolated Python **3.11.6**, PostgreSQL **16.11**, Pillow **13.0.0**, Streamlit **1.67.0**. Database and HTTP services are dedicated loopback synthetic-demo instances. Current machine evidence is `artifacts/audit/summary.json`; historical release results are not substituted for this audit.

The final correction-review verdict and any later exact-commit clone/CI checks are recorded separately when completed. An absent or pending record is not a passed gate.

## Complete current-candidate gate — executed

Working directory: repository root. Interpreter: `.venv/Scripts/python.exe`.

```bash
.venv/Scripts/python.exe -m pytest tests/test_reproducibility.py -q --tb=short
.venv/Scripts/python.exe -m ruff format queryguard scripts tests workspace.py
bash scripts/verify.sh
.venv/Scripts/python.exe -m pip check
bash -n scripts/run_api.sh scripts/run_ui.sh scripts/verify.sh
.venv/Scripts/python.exe scripts/smoke.py
.venv/Scripts/python.exe scripts/record_verification.py
```

All listed commands exited **0**. `verify.sh` ran actual bootstrap, lint, formatter check, compilation, the then-complete 94-test suite and evaluator. After a final evaluation-table rendering correction, the complete suite was rerun with `.venv/Scripts/python.exe -m pytest -q --tb=short --junitxml=artifacts/pytest.xml`: **95 passed**. Lint/format/compilation and evidence checks were repeated; unchanged backend evaluation results below were retained rather than rerunning them for a UI-only presentation change.

|Gate|Actual result|
|---|---|
|Complete pytest|**95 passed, 0 failed, 0 errors, 0 skipped**, one library deprecation warning; console elapsed **24.33 seconds**|
|JUnit accounting|95 tests; JUnit suite time **24.256 seconds**; slight runner/console timing differences are not separate tests|
|Additional regression cases versus the original 65-test suite|**30**; computed from the executed suite count, not claimed as 95 newly authored tests|
|Reproducibility-specific subset|**11 passed** before integration|
|Ruff lint|All checks passed|
|Ruff formatting|28 Python files already formatted|
|Compilation|Exit 0|
|Dependency consistency|`No broken requirements found`|
|Shell syntax|All three scripts passed|
|Live HTTP smoke|Four expected query outcomes, isolated history, live schema, evaluation HTTP 200, UI health HTTP 200|
|Recorded local-secret scan|Zero matches for actual local DSNs/passwords in the scanned publishable text; exact scan scope in `artifacts/verification.json`|

The warning comes from installed Starlette/FastAPI TestClient's deprecated httpx integration. It is not silently counted as a failure or hidden by warning filters. No arbitrary dependency replacement was made merely to suppress it.

## Actual evaluation — SIMULATED/TEMPLATE, not an LLM

Fixture: deterministic seed **v2**, 48 customers, 12 products, 360 orders and 720 items. Independent PostgreSQL queries measured **576 item prices differing from the current catalog**, with **40 customers having six orders** and **eight having 15 orders**. This deliberately improves semantic discrimination; it is not a realistic production distribution.

|Executed setting|Correct / total|SQL valid / expected queries|Execution-equivalent queries|Correct nonquery outcomes|Mean ms|p95 ms|
|---|---:|---:|---:|---:|---:|---:|
|baseline template|105/105|78/78|78/78|27/27|107.830|207.658|
|schema-aware template|105/105|78/78|78/78|27/27|107.762|202.704|

- There are **105 unique fixture records reused across two settings**, not 210 independent questions or a held-out model study.
- Nonquery records comprise 12 clarifications and 15 refusals. No evaluation cases were skipped.
- **40/40** supplied adversarial SQL cases were rejected by executed policy calls before unsafe SQL reached PostgreSQL. Connected-join regression cases are additional tests, not silently added to this corpus denominator.
- Reference SQL is executed independently on the same restricted database and compared using typed values, row multiplicity, declared ordering and numeric tolerance. A deliberately wrong reference and the new historical-price/strict-threshold semantic mutations are detected by tests.
- Templates ignore prompt text. Equal scores do not measure prompt improvement, schema-retrieval quality or language generalization.
- Latency is this local template pipeline's measured timing, varies with load and is not production throughput or live-model performance.

Raw per-case SQL, typed results, statuses, timings and fixture hashes: `artifacts/evaluation.json`. Readable generated report: `artifacts/EVALUATION.md`.

## Browser journeys — executed against the running application

`artifacts/audit/browser-journeys.json` contains **12 passing checks**:

- updated application startup;
- joined category revenue accepted, SQL/result controls rendered;
- ambiguous revenue clarified;
- password request refused;
- monthly revenue accepted;
- **actual CSV download**, parsed as two columns and 12 data rows;
- schema, evaluation and history tabs;
- cleared history with no remaining chat messages;
- keyboard Tab focus movement;
- 390-pixel mobile workspace with no document-width overflow.

Console hooks were installed before navigation; no errors were recorded on the checked interactions. These are specific exploratory browser checks, not a broad accessibility certification or a claimed cross-browser Playwright suite. Provider/error/component tests use explicitly labelled HTTP doubles; browser/DB/API paths were exercised separately against real services.

## Baseline and reproduction evidence — do not merge denominators

1. **Parent's original baseline:** 64 passed, one Streamlit AppTest timeout at 30 seconds; total run 61.35 seconds. The test mixed component rendering with uncontrolled live HTTP dependencies. Exact contributions of cold imports/load/network timing were not conclusively isolated. The component test now uses an explicit double; real browser/API journeys remain a separate gate.
2. **Independent security subset:** 54 targeted tests passed; the independent reviewer deliberately did not run mutating bootstrap tests. It also reran the 105-case template mode and 40 attacks. This was not another complete suite.
3. **Original remote clone:** an actual clone of `19472ec`, fresh Python 3.10 environment and genuinely empty isolated PostgreSQL cluster. Locked install succeeded after an initial 420-second interrupted attempt. With additional manual database setup, 65 tests passed and both 105-case modes/40 attacks passed. Literal concurrent default-port setup and wheel installation failed. See `artifacts/audit/baseline/clean-clone-review.md`.
4. **Repaired source export:** a separate fresh Python 3.11 source environment, successful native bootstrap and 93 tests passed, one warning, 28.83 seconds; both evaluation settings passed 105/105 and 40 attacks were rejected. This was a repaired-source export, **not falsely labelled a later public remote clone**. It predates the added measured-bootstrap-count regression and final changes listed in `artifacts/audit/reproduction.json`; the parent subsequently ran the current 95-test suite.
5. **Application wheel:** build/install remains unsupported; the observed package-discovery failure is retained, not relabelled as a successful packaged deployment. The README supports source-checkout execution instead.

## Dependency advisory check — executed, narrower than security proof

The OSV API was queried for all **61 pinned Python packages**, and installed metadata matched those pins. Original Pillow 12.3.0 matched advisories; inspected primary records included `GHSA-22hg-r758-rrw9` and `PYSEC-2026-4363`, fixed in 13.0.0. Advisory identifiers can alias the same underlying vulnerability, so they are not counted as independent application exploits.

The repaired pins matched **zero OSV advisories at the recorded time**. This does not audit every interpreter/OS/native/image component or establish exploitability. No attacker-controlled image upload path was demonstrated. Streamlit 1.65.0's Pillow<13 constraint caused a real resolver failure; compatible 1.67.0 plus Python 3.11 resolved it, and the new environment installed successfully. Evidence: `artifacts/audit/dependencies.json`.

## Not executed or not established

Live Ollama inference, held-out model quality, complete application Compose build/run, standalone application wheel success, production authentication, distributed operational behavior, load/endurance testing, exhaustive fuzzing/penetration testing, complete static typing and exhaustive accessibility. A prior green Ubuntu release workflow is historical; any current-candidate CI result must carry its own exact tested SHA and job evidence. See `KNOWN_LIMITATIONS.md`.
