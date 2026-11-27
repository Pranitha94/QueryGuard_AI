# Comprehensive audit — QueryGuard AI

## Final closure — executed

The independent correction review passed. The repaired published checkout at `a6f02579a310ee0ce38c0a62bd6972cea8e0b646` subsequently passed **95 tests**, both **105/105 simulated-template evaluation settings**, **40/40 policy attacks**, dependency consistency, and isolated API/UI smoke checks against its newly initialized PostgreSQL instance. GitHub Actions run **45978053452** completed successfully for that exact SHA. All isolated verification services were stopped and ports rechecked closed. Evidence: `artifacts/audit/final-review.json`, `exact-clone.json`, `github-ci.json` and `closure.json`.

The clone check exposed and corrected Windows shell-script CRLF checkout and an ambient-URL assumption in one test. Those post-review changes were limited to `.gitattributes` and two test-isolation lines; application Python/SQL behavior did not change. Dependency installation timed out once before a bounded recovery; no interrupted command is counted as success. The existing clone needed Git to regenerate its shell files under the new LF policy. Explicit exports inside Git Bash were used for isolated service launch; the native-to-MSYS harness did not preserve overrides. Clone verification wrote its default artifacts and is not falsely described as source-clean. The supported path remains a source checkout, not an application wheel.

This follow-up changes only documentation/evidence and uses `[skip ci]`; the passing CI SHA above is stated explicitly rather than presented as a run of the later documentation commit.

## Executive verdict

**A working, substantially tested local portfolio demonstration—not a production-ready analytics service or demonstrated general-purpose LLM agent.** The audit found real boundary, correctness, setup and documentation defects despite the earlier green release. Confirmed critical/high-priority remediation was prioritized, and several medium/low defects were also corrected with regression tests.

The corrected native candidate executed **95 tests successfully**, versus the original 65-test suite, and passed the actual template evaluator and live API/browser checks. These are measured results, not a substitute for a final independent correction review or exact-commit reproduction/CI evidence. Those closure checks are recorded separately as they finish; pending checks are not called passed.

No destructive SQL execution, privilege escalation, approved-table confidentiality bypass or exposed real credential was reproduced in the tested synthetic/local boundary. That statement is narrower than “secure”: a finite review and attack corpus cannot prove complete security. The one high-priority finding was a known-affected dependency combination, **not a demonstrated remote image-upload exploit in this application**.

## Audited scope and methodology

- Original revision: `19472ece9771c5530439365d57fe95aa6b176f6a`, repository `Pranitha94/QueryGuard_AI`.
- Main workspace: `D:/Hermes/Pranitha_projects/queryguard-ai`; no neighboring project was audited or modified.
- Inspected API, UI, SQL policy, executor, PostgreSQL roles/bootstrap/schema, provider/prompt boundary, evaluation fixtures/comparison, test design, dependencies, scripts, Docker/CI configuration, reports, screenshots and resume claims.
- Ran a fresh baseline before remediation. Independent read-only security and clean-clone reviewers investigated separately; their original reports are retained under `artifacts/audit/baseline/`.
- Used actual synthetic PostgreSQL, API and browser journeys. Used explicitly labelled HTTP doubles for controlled provider/UI failures. No paid APIs, model pulls, real customer data or unsafe privileged SQL probes.
- Added regression-first corrections; final native integration ran bootstrap, Ruff, formatting, compilation, complete pytest, actual evaluation, dependency consistency, shell syntax and HTTP smoke.
- Checked a primary advisory service separately from `pip check`. A source-only installation was distinguished from a successful wheel. A fixed-source export was distinguished from an actual remote clone.

Detailed commands/counts: [TEST_RESULTS.md](TEST_RESULTS.md). Scope of implemented claims: [VERIFIED_FEATURES.md](VERIFIED_FEATURES.md). Residual risk: [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## Findings and disposition

|ID|Priority|Observed finding|Disposition|
|---|---|---|---|
|A01|High dependency-remediation priority|Pillow 12.3.0 matched published advisories; old Streamlit constrained Pillow below the fixed release|Fixed with compatible Python 3.11+, Pillow 13.0.0 and Streamlit 1.67.0; install/tests/advisory recheck executed|
|A02|Medium|Equality-join check permitted a newly introduced alias absent from the ON predicate|Fixed with same-scope source-connectivity validation and regression|
|A03|Medium|Infinity/NaN/extreme numeric results caused HTTP 500 after an accepted audit event|Fixed by checking HTTP encoding before final status/audit; three actual-DB numeric regressions|
|A04|Medium robustness|Provider byte guard ran after the entire HTTP body was buffered|Fixed with bounded streaming consumption, response closure and identity-encoding policy|
|A05|Medium robustness|Question length did not limit the HTTP body buffered before JSON validation|Fixed with a 16,384-byte streaming POST budget; fixed/chunked request regressions|
|A06|Low robustness|Audit mkdir/stat/rotation faults bypassed sanitized 503 handling|Fixed; filesystem-failure/rotation/slot-release coverage added|
|A07|Medium UX|Expired/evicted UI token had no automatic recovery path|Fixed: renew after 401 and retry the rejected request once; old UI messages cleared|
|A08|Low UX|A history-clear HTTP failure raised an uncaught Streamlit traceback|Fixed: safe error display instead of losing the page|
|A09|Medium evaluation quality|Uniform prices/order counts let important wrong SQL match expected results|Fixed in seed v2; historical-price and strict-threshold mutations now fail|
|A10|Medium reproducibility|External bootstrap failed when the dedicated database did not yet exist|Fixed through maintenance-db creation, explicit target/reader validation; tests added|
|A11|Medium reproducibility|DB/API/UI/smoke ports were hardcoded, preventing safe concurrent checkout verification|Fixed with validated port/URL options and evidence-output controls|
|A12|Low test reliability|A component-render test depended on uncontrolled live services and timed out in the audit baseline|Isolated with an explicit HTTP double; real browser/API journeys retained separately|
|A13|Low provenance/UX|Configured live-provider mode still showed the template-only banner|Fixed with provider-aware wording; configuration is not claimed as successful inference|
|A14|Low reporting|Bootstrap printed expected row counts as a constant|Fixed: output now queries actual row counts; regression uses differing controlled counts|
|A15|Medium distribution gap|`pip install .` / wheel creation failed flat-layout discovery|Not presented as repaired: README explicitly supports source checkout only; full application wheel remains unsupported|
|A16|Low documentation|README omitted executable clone/venv steps, alternate-port/external-db prerequisites and report provenance|Corrected; historical/fresh reports and original/fixed-source reproduction are distinguished|
|A17|Medium operational limitation|Provider inactivity timeout is not a total request deadline|Remains explicitly documented; no public/production availability claim|
|A18|Low product/architecture limitation|Rich SQL narration, large-schema retrieval gains and production-scale operational behavior were not demonstrated|Not counted as verified features; clear scope/limitations retained rather than placeholders|
|A19|Low visual/accessibility robustness|The two-row evaluation canvas grid intermittently painted blank in browser captures despite correct accessibility values|Replaced with a simpler plain HTML summary table; component regression and actual visible-table values verified without resize|
|A20|Medium Windows reproduction|Git autocrlf converted shell scripts to CRLF and Git Bash rejected pipefail|Fixed with *.sh text eol=lf; corrected checkout completed the integrated suite and HTTP checks|
|A21|Low test isolation|An inherited endpoint URL invalidated a test that expected port-only defaults|The test now clears ambient URL overrides; targeted regression, cloned 95-test suite and CI passed|

No critical defect was reproduced. Priorities reflect the documented local/synthetic trust boundary, not a claim that internet exposure would be safe.

## Important reproductions and minimal corrections

### A01 — advisory and resolver evidence

A real OSV query of all 61 original pins identified Pillow as affected. Inspected records included `GHSA-22hg-r758-rrw9` (crafted image handling can hang a worker) and `PYSEC-2026-4363` (affected TIFF encoding can disclose memory/crash); both identify fixed release 13.0.0. Advisory IDs may alias vulnerabilities and are not counted as independent application exploits. No untrusted image-upload route was demonstrated.

Primary package metadata showed Pillow 13.0.0 requires Python>=3.11. The attempted install with Streamlit 1.65.0 **actually failed resolution** because it required Pillow<13. Compatible Streamlit 1.67.0 supports the fixed version. The project environment, minimum version, Docker base and CI interpreter were updated together; the new environment installed, `pip check` passed and installed metadata matched all 61 pins. The repeat OSV query returned no matches at its recorded time. This does not audit the OS/interpreter/native image stack or prove complete dependency safety.

Evidence: `artifacts/audit/dependencies.json`; runtime guard regression `test_supported_runtime_uses_fixed_pillow_release`.

### A02 — a syntactically valid disconnected join

The original validator accepted:

```sql
SELECT COUNT(*)
FROM analytics.orders o
JOIN analytics.customers c ON o.customer_id=c.customer_id
JOIN analytics.order_items i ON o.customer_id=c.customer_id
```

The second predicate never connects `i`. Independent read-only execution returned **259,200**, amplifying intermediate work and producing a misleading business query despite the no-Cartesian claim. LIMIT does not bound aggregate input. The fix requires the newly introduced alias and an earlier source in the same SELECT scope, before and after qualification. It does not certify that every equality is the correct business relationship.

RED: `test_policy_rejects_join_predicate_that_omits_new_alias` failed to raise. GREEN: the regression and valid-provider/policy subset passed; the complete 105-case modes subsequently passed.

### A03 — serialization is part of the API boundary

Original actual-DB proposals such as `SELECT CAST('Infinity' AS DOUBLE PRECISION) AS value` passed policy/execution but failed JSON encoding. The API returned 500 while history said accepted. NaN and an extreme NUMERIC reproduced the same boundary problem.

The corrected API validates JSON representability before recording success. Covered unsupported values become a sanitized `execution_error` with no rows, and history records that outcome. This does not promise that a client always receives a response after a network disconnect; it fixes the observed server-side encoding failure.

RED: all three numeric regression cases returned 500. GREEN: all three and API regressions passed.

### A04/A05 — measure bytes at transport boundaries

The original provider consumed an entire synthetic 1 MiB response before checking its 64 KiB limit. The new adapter stops receiving after its budget and closes the response; a test verifies that a tail chunk is not consumed. Compressed output is refused rather than permitting decompression amplification. This is HTTP-double evidence, not live model inference.

Separately, the independent reviewer sent a roughly 2 MiB whitespace-padded JSON request with a short valid question and received an ordinary outcome. The new ASGI guard bounds POST bytes before JSON decoding/provider work, including bodies without a reliable Content-Length. Fixed and streamed request tests changed from accepted to HTTP 413 with no provider invocation. There is still no global connection/memory budget or strict whole-request deadline.

### A06–A08/A12/A13 — error paths and test honesty

Directory and rotation failures reproduced unhandled 500s; now all audit filesystem steps are within sanitized handling, the history is not falsely appended and slots are released. API expiry/eviction, rotation and overlapping-capacity coverage were added.

UI doubles reproduced stale tokens and a history-clear 503 traceback; both now recover or render a safe error. A configured Ollama double also reproduced the inaccurate template banner; the new wording distinguishes configuration from inference.

The original baseline had 64 passes and one AppTest timeout. Its exact load/import/network contribution was not conclusively isolated. The component test now controls its HTTP boundary, while 12 separately recorded real browser checks retain actual UI-to-service coverage. No claim is made that mocks proved a working live provider or solved a production server timeout.

### A09/A14 — distinguish legitimate templates from hardcoded answers

The default SQL patterns are intentionally hardcoded and clearly labelled. Result rows are calculated by PostgreSQL; runtime providers do not import answer-key fixtures. The independent evaluator really executes reference SQL and compares results. No fabricated metric was found in those executed records.

Nevertheless, the old seed made every historical item price equal today's catalog price, so the wrong-price mutation still passed. Customer order counts of seven/eight also left several high-threshold cases empty. Seed v2 retains the same table counts but has **576 historical/catalog price differences**, 40 six-order customers and eight 15-order customers. A wrong current-price query and an inclusive-versus-strict threshold now demonstrably fail evaluation. This is better regression discrimination, not held-out AI research.

Bootstrap's constant expected-count message was also replaced by actual count queries. This reporting fix is separate from the evaluator, whose executed metrics were already real.

## Database and architecture review

**Strengths:** explicit small modules; provider→policy→execution separation; executor re-review even for constructed `ReviewedSQL`; actual runtime privilege checks; true ACL-denial tests independent from read-only defaults; PK/FK relationships; strict statuses; independent typed evaluator; data-minimal audit; plain-text untrusted UI and CSV formula neutralization.

**Tradeoffs:** repeated metadata/privilege queries and per-request HTTP clients cost round trips; no throughput/load evidence justifies optimizing with caches yet. Broad sanitized exceptions favor confidentiality but reduce diagnosis unless supported by safe internal telemetry. Locks/sessions/audit are one-process only. No tenant identity system exists. A rich SQL explanation is not implemented merely because reviewed SQL and a row-count summary are displayed.

The tiny trusted schema, explicit query subset and local deployment boundary are central assumptions. Additional SELECT/function/sequence/ownership changes are not comprehensively attested. Do not widen database scope or expose HTTP ports without a new threat model and authorization design.

## Reproducibility and packaging assessment

The independent reviewer actually cloned the original remote, installed a fresh environment and initialized new isolated PostgreSQL storage. The original app ran after manual DB creation, but literal concurrent default-port commands and `pip install .` failed. Initial dependency installation also timed out before one bounded successful recovery; that interruption was not called success.

A separate repaired-source export used a new Python 3.11 environment and successful native bootstrap, passed 93 tests and both 105-case settings/40 attacks. It was not falsely described as a later public clone. The parent then executed the complete current 95-test suite including subsequent measured-reporting and plain-table rendering regressions. Differences between repaired export and current source are explicit in `artifacts/audit/reproduction.json`.

The README now supports a source checkout, executable clone/venv steps, validated alternate ports and consistent external DSNs; the repaired script creates an absent dedicated database. Redirected evidence has explicit options. The UI's saved report remains historical until its documented report file is regenerated. Wheel distribution remains unsupported rather than hidden behind a passing source-root import. Full Compose application execution remains unverified even when configuration parsing or a CI PostgreSQL service succeeds.

## Verification and artifact integrity

- Current native integrated suite: **95 passed, zero failures/errors/skips**, one library warning.
- Actual template evaluation: **105/105** in each setting, **78/78** query results and **27/27** nonquery outcomes per setting; **40/40** supplied policy attacks rejected.
- Actual browser evidence: **12 checks passed**, including a downloaded/parsed CSV, mobile width and keyboard focus movement.
- OSV: all **61 repaired pins** checked, installed metadata matched, no advisory matches at that timestamp.
- Machine evidence: `artifacts/pytest.xml`, `evaluation.json`, `http-smoke.json`, `verification.json` and `artifacts/audit/`.
- No real local DSN/password matches were found in the recorded publishable-text scan. Dummy CI/test credentials are labelled synthetic and are not presented as production secrets.

Historical reports are retained as labelled evidence, not summed into the final test count. Corrected-source approval must be bound to a frozen file manifest; the final independent verdict is separate from the original reviewers' findings. Final delivery must also validate all eight document paths, the **40 complete numbered Q&A sections**, and demo segments totaling **120 seconds**.

## Hiring-manager assessment

**Credible junior/early-mid backend or applied-AI integration portfolio, provided the candidate can explain the actual boundaries and corrections.** Good discussion topics include why prefix checks fail, why read-only flags are not permissions, how joins/lineage are resolved, how independent execution testing works and why template scores are not model accuracy.

The project does not establish senior security ownership, production scale, real customer impact or LLM research expertise. The strongest professional signal is admitting and reproducing real defects, correcting them with tests, and preserving the difference between implemented, simulated, executed and unverified. A candidate who markets this as “fully secure AI with 100% model accuracy” would contradict the evidence.

Use `INTERVIEW_QUESTIONS.md`, `COMPONENT_GUIDE.md` and the timed `DEMO_SCRIPT.md`. Resume bullets deliberately avoid invented employment, users, deployment status or business impact.

## Residual risk and closure

Live Ollama inference, held-out/generalization evaluation, standalone application wheel, full application Compose run, production authentication, distributed controls, load/endurance testing, exhaustive fuzzing/penetration testing, complete typing and full accessibility remain outside verified scope. A strict provider/request wall-clock deadline remains an operational limitation. See `KNOWN_LIMITATIONS.md`.

Current native gates above are executed. A final independent correction verdict and any subsequent exact-commit clone/CI checks are recorded as distinct closure evidence; their absence must not be read as success. No production-readiness claim is made.
