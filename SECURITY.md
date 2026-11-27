# Security model and limitations

## Intended boundary

Local, single-user portfolio demo over a dedicated **synthetic** PostgreSQL database. No real PII, contact details, business credentials, row samples, paid APIs or model downloads. API/UI default to loopback. Session tokens provide bounded history isolation, not user authentication or authorization. Anyone who can reach the API can create a session and query the synthetic dataset. Do not expose it to the Internet or connect it to a production database.

Assets: database integrity, approved-table confidentiality, host filesystem/network boundaries, credential secrecy, query resource budget, session isolation and accurate provenance. Adversaries: malicious questions, prompt injection, untrusted model proposals and invalid SQL. Trusted: host administrator, setup code, fixed schema/seed, committed evaluator fixtures and optional local model server configuration. A compromised host, malicious dependency or database superuser is outside this demo's security guarantee.

## Defense in depth

|Boundary|Implemented control|Executed evidence|
|---|---|---|
|Question → provider|16,384-byte POST body budget before JSON decoding, 2,000-character question limit, strict Pydantic shape, no echoed invalid input, explicit untrusted schema/question JSON, no row samples|API tests, fixed/chunked body-budget regressions and provider contract tests|
|Model → SQL|Strict Proposal schema; refusal/clarification cannot execute SQL; streaming 65,536-byte body guard and identity encoding; invalid/timeout responses never silently fall back|Ollama HTTP doubles and early-stop regression, not a live model run|
|SQL syntax/scope|Single SELECT/CTE/set statement; explicit AST node/function/type/table/column allowlists; reject unsupported constructs at every depth; qualified lineage resolution plus second review|40 reviewable attacks, generated actual rejection evidence|
|Complexity|12,000 SQL characters, 1,000-character literals, 300 AST nodes, depth 18, 4 equality joins, no cross/lateral/recursive/window queries, 200-row ceiling|Policy/adversarial/row-bound tests|
|Database execution|Separate noinherit/nonprivileged reader, explicit column grants, no memberships/superuser/bypass/create/temp/write privileges; startup and per-execution role checks; read-only transactions, 2,000-ms statement and 500-ms lock timeouts|Real PostgreSQL tests; ACL negatives explicitly switch READ WRITE first|
|Resource envelope|4 in-process query slots, 5-second connection timeout, bounded fetch, bounded sessions/history/audit|Limit/history tests; no production load benchmark claimed|
|HTTP serialization|Reject nonfinite/unsupported numeric response encoding before reporting accepted success or recording the audit status|Actual PostgreSQL Infinity, NaN and extreme-numeric regressions|
|History/audit|100 sessions maximum, 1-hour expiry, 50 metadata entries each; audit rotation around 1 MB plus one prior segment; no questions/SQL/results/tokens/DSNs/raw exceptions|Expiry/eviction, concurrency, rotation and filesystem-error regressions; audit includes status/provider/mode/time/count/request ID only|
|Parser diagnostics|Suppress SQLGlot warnings which otherwise echo full rejected SQL; return sanitized policy errors|Regression reproduces parser warning leakage and verifies suppression|
|UI/export|Code/text/JSON for untrusted content; no model-generated HTML; CSV formulas neutralized in headers and cells|CSV tests and actual browser capture|
|Deployment recipes|Loopback HTTP publication, no published DB port, internal DB network, separate setup vs runtime credentials, nonroot app image|Compose configuration validated; images/containers not built or run|

## Deliberate SQL restrictions

Unknown constructs fail closed, even legitimate analytical SQL. Stars are disallowed except `COUNT(*)`; no arbitrary PostgreSQL functions, catalog reads, foreign schemas, locks, `SELECT INTO`, recursive CTEs, DML-in-CTE, user-defined casts, table functions, window functions, OFFSET, Cartesian joins or arbitrary join predicates. Joins require explicit equality connecting the newly introduced alias to an earlier source in the same scope. This restricts expressiveness; it does not prove logical correctness or provide row-level tenant authorization.

`qualify()` resolves names; it is not itself an authorization mechanism. The custom allowlists run before **and after** qualification, and executable SQL is serialized from the reviewed AST, never the original model string. `execute()` re-reviews even a manually constructed `ReviewedSQL` and verifies the actual connection's role. Builtin functions rely on a trusted, non-writable analytics schema; untrusted admins/schema owners are not in scope.

## Residual risks and unverified claims

- No independent penetration test, formal proof, exhaustive grammar fuzzing, complete supply-chain attestation, TLS, SSO/RBAC, distributed rate limiting, global multiworker session consistency or production threat certification. A recorded OSV query of all pinned Python packages did run; it found the old Pillow pin affected and the repaired pins had no matches at that time. See `artifacts/audit/dependencies.json` for precise scope, advisory identifiers and limitations.
- Local callers/host administrators can access their own synthetic results; secrets in native `.env` remain readable by the host user. Docker separates setup credentials from runtime environment more strongly, but that deployment has not been executed.
- PostgreSQL's administrator-controlled logs may include SQL/error statements. Application audit is data-minimal, but do not assume host/DB debug logs are sanitized. They are gitignored and must not be published. Use appropriate database logging controls before any sensitive deployment.
- Statement timeouts limit individual statements, not an end-to-end request deadline. Connection/provider/network delays add latency. A synthetic loopback drip-server probe confirmed that HTTP inactivity timeouts are not total deadlines; live Ollama inference and resource-exhaustion/load testing were not executed.
- Bounded audit rotation is process-local, not a tamper-proof durable audit system. Use one API worker. No cross-process session sharing.
- A small deterministic dataset cannot expose every semantic SQL bug. The benchmark is template-covered and intentionally not a held-out LLM test.
- Ollama/live LLM and Docker container execution remain unverified. Compose was parsed with synthetic validation credentials; Docker daemon was reachable but required base images were absent, and no large image/dependency downloads were undertaken.
- Static typing was not run. Lint and bytecode compilation are not a substitute for runtime or security tests.

## Handling a suspected issue

Stop only this project's API/UI/database, preserve minimal sanitized reproduction SQL on synthetic fixtures, add a regression test, and review every boundary before widening an allowlist. Never paste `.env`, database log contents, DSNs, session tokens or real records into a public report or model prompt. Rotate exposed local credentials and recreate only this dedicated synthetic instance when appropriate. Do not claim a passing attack corpus establishes complete security.
