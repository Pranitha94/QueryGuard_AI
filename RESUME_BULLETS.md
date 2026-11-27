# Resume bullets — verified scope only

Choose two or three; do not describe the simulated provider as a live LLM or extrapolate these fixture results to general model quality.

- Added regression-tested request/provider byte budgets, JSON-safe numeric error handling, connected-join validation, audit fault handling and UI session recovery; validated the repaired local application with **95 passing automated tests** and real PostgreSQL/API/browser checks.
- Built a PostgreSQL-backed analytics workspace with FastAPI, Streamlit and Plotly, exposing reviewed SQL, interactive charts, formula-neutralized CSV exports and session-isolated query history over four deterministic synthetic business tables.
- Implemented a fail-closed SQLGlot AST/lineage policy and least-privilege PostgreSQL execution boundary with column-specific SELECT grants, startup/per-query role checks, a 200-row cap and a 2-second statement timeout; exercised 40 distinct adversarial SQL cases with recorded policy rejections.
- Authored 105 independently reviewable benchmark questions and an evaluator that independently executes reference SQL and compares typed, order-aware/multiset results; verified all 105 documented template cases in both baseline and schema-aware modes, explicitly labeling generation as simulated rather than LLM inference.
- Added a modular Ollama JSON-schema adapter with strict Pydantic validation and HTTP-double coverage for success, timeout and malformed outputs, without silent fallback; supplied reproducible environment pins, PostgreSQL CI and Docker recipes with execution limitations documented.

Evidence: `TEST_RESULTS.md`, `AUDIT_REPORT.md`, `artifacts/evaluation.json`, `artifacts/EVALUATION.md`, `artifacts/pytest.xml`, `artifacts/http-smoke.json`, `artifacts/audit/browser-journeys.json`, `artifacts/audit/dependencies.json` and actual browser screenshots under `docs/screenshots/`. Historical checkpoints remain in `docs/VERIFICATION.md`.

Do **not** claim production deployment, live Ollama accuracy, measured prompt improvement, live Docker execution, real-customer data, exhaustive security, paid API integration, held-out model generalization, or performance at production scale.
