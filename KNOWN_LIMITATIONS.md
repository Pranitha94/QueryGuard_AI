# Known limitations — QueryGuard AI

Read alongside `AUDIT_REPORT.md`, `VERIFIED_FEATURES.md` and `TEST_RESULTS.md`. These limits are not waived by passing tests or a dependency scan.

## Product and AI scope

- **Default generation is SIMULATED/TEMPLATE.** It supports a documented vocabulary, not arbitrary natural language. The SQL templates are predefined, while result values are calculated by PostgreSQL.
- **No live Ollama inference was executed in this audit.** The adapter, strict output parsing, response-size handling and error paths have automated HTTP-double coverage. Provider configuration alone does not prove an installed model works.
- No held-out model benchmark, paraphrase/generalization study, model-version comparison or demonstrated prompt-quality improvement. Baseline/schema-aware equivalence is expected because the template ignores prompt text.
- The schema is tiny and connected; relationship closure frequently returns all four tables. This is not evidence of efficient retrieval over hundreds of tables.
- Clarification is a structured outcome, not a durable multi-turn reasoning engine. Unknown requests may be refused even when an expert could express a safe SQL query.
- Results have a basic row/column-count summary and an SQL viewer. A rich plain-language explanation of each SQL operation, causal business narrative, forecasting and general chart recommendation are not implemented. Chart selection is a simple result-shape heuristic.
- Gemini integration was optional and is not implemented. There is no hidden paid-API dependency or fallback pretending to be live inference.

## Security and operations

- **Local, single-user, synthetic-data trust boundary.** Opaque session tokens isolate history; they do not authenticate people or provide tenant authorization. Do not expose the API/UI publicly.
- Query/session/history limits and locks are process-local. Multiple workers would not share those controls. Anyone able to reach the local session endpoint can create sessions and cause older ones to be evicted.
- SQL authorization is an explicit conservative subset, not every PostgreSQL query. Equality-join connectivity is checked, but the application cannot guarantee that a model chose the correct business relationship or metric.
- A finite adversarial suite is not an exhaustive grammar audit or proof of complete security. No independent penetration test or production threat-model validation was performed.
- HTTPX transport timeouts are per-operation/inactivity limits, **not a strict end-to-end wall-clock deadline**. A slow local provider can still occupy query slots. The request-body and provider-byte budgets do not establish a global process memory or concurrent-connection budget.
- The 200-row ceiling limits output, not all intermediate work. Statement/lock timeouts and AST complexity limits mitigate expensive SQL but are not a cost-based workload governor.
- Audit/history intentionally exclude raw questions, SQL, results and tokens. The bounded local audit is not durable, shared, tamper-evident or compliance-certified logging. A failed audit prevents a successful query response, but cannot undo a read already performed.
- PostgreSQL administrator-controlled logs can contain SQL or error statements. Those ignored host logs are outside the application's sanitized audit guarantee.
- Database administrators, schema owners and local model-server configuration remain trusted. Runtime privilege verification does not comprehensively attest every executable function, sequence, database owner change or hostile host modification.

## Evaluation and data

- All records are synthetic, small and deterministic. No real customer, employer, production or client-impact claims are supported.
- The benchmark is a functional regression suite aligned with implemented templates, not independently held-out language tasks. Parameterized month/threshold questions are not independent reasoning discoveries.
- Seed v2 introduces historical-price differences and unequal customer order counts, and regression tests show that two previously invisible semantic mutations now fail. This improves discrimination but does not make the fixed fixture comprehensive or statistically representative.
- Numeric result comparison uses a documented tolerance and floating conversion. It is not exact financial accounting validation at arbitrary magnitude.
- Saved reports and screenshots are historical evidence, not live monitoring. A clone can initially display the committed report until its evaluator is rerun. Check timestamps, fixture hashes, provider labels and the revision tested.

## Deployment, dependencies and verification limits

- Full application Docker Compose build/run was not verified merely by validating configuration or using a PostgreSQL service in CI. Treat the Compose recipe according to the actual execution status in `TEST_RESULTS.md`.
- Dependency pins are not hash-verified downloads; image and GitHub Action tags are mutable. No complete supply-chain attestation was performed.
- The OSV check queried pinned Python packages at a recorded time. Zero matches after remediation does not mean zero vulnerabilities; interpreter, OS, container images and all native libraries were not comprehensively audited. The native audited interpreter is Python 3.11.6; use a supported security-patched interpreter for any broader deployment.
- No load/endurance test, exhaustive accessibility/WCAG review, broad browser/OS matrix or completed static type-checking gate is claimed. Browser checks cover specific desktop/mobile journeys and keyboard focus, not universal accessibility.
- Reproduction evidence must distinguish original remote revision, repaired source candidate, package-core installation and source-based full application execution. See the precise current scope in `AUDIT_REPORT.md`; do not infer that a successful import proves a standalone application wheel.

## Hiring interpretation

Present this as a defensible junior/early-mid backend or applied-AI integration project. Its strongest evidence is explicit safety boundaries, PostgreSQL permissions, actual execution-based tests and honest limitations. It does not demonstrate senior security ownership, production platform scale or measured general-purpose LLM capability.
