# Implementation plan

1. **Bootstrap / dataset vertical slice**: isolated Python 3.10 venv; deterministic four-table PostgreSQL seed; separate generated admin/runtime secrets; real integration test observes missing seed, then checks counts and denied writes. Gate: PostgreSQL bound to loopback 55432, SCRAM and least privilege.
2. **Guarded execution slice**: test approved SELECT then fail-closed AST policies, lineage and limits; implement/retest each behavior family. Gate: safe execution and actual role privilege negatives; no raw-error leakage.
3. **Provider / service slice**: test deterministic templates and structured Ollama success/error with HTTP doubles; schema introspection/retrieval; query orchestration and bounded isolated history/audit. Gate: FastAPI actual database E2E, provider failures do not fall back.
4. **Evaluation slice**: manually inspectable >=100 questions and >=30 attack records; independently execute references, typed comparisons, baseline and schema-aware actual runs. Gate: committed per-case measured reports, honest template-only labels.
5. **Workspace / delivery slice**: Streamlit Plotly UI, Docker/CI/startup, security and interview docs. Gate: complete pytest, compile/lint, real HTTP API/UI probes, actual benchmark and attack suite, final review regression tests.

Strict vertical RED -> GREEN cycles recorded in docs/VERIFICATION.md. No commits, pushes, external paid APIs, model downloads, unrelated services or personal data. Docker/live LLM execution explicitly unverified if unavailable.

## Implementation-stage outcome — November 26, 2026 (historical)

Publication and successful Ubuntu GitHub CI were subsequently verified by the parent; see `docs/VERIFICATION.md` and `artifacts/github-ci.json`. The implementation-stage limits below describe the earlier checkpoint.

Native delivery gates completed: seeded isolated PostgreSQL 16.11 on loopback 55432; guarded FastAPI service on loopback 8000; actual Streamlit/Plotly workspace on loopback 8501; final regression 65 passed / 0 failed / 0 skipped (one installed-library deprecation warning); 105 independently reviewable benchmark records passed in each simulated template setting; 40/40 policy attacks rejected. Real HTTP smoke, browser screenshots, lint/format/compile, dependency consistency and local-secret exclusion checks executed. Actual evidence and exact RED/GREEN commands are in docs/VERIFICATION.md and artifacts/.

Optional/deployment limits: Ollama adapter contract-tested with HTTP doubles only, no live model downloaded/executed. Docker daemon reachable and Compose configuration validated, but required base images absent; no large image downloads/container build/run. CI recipe authored, not published/run remotely. Static typing, clean-room/Linux installation and independent penetration/load testing remain unverified. No production/complete-security/general-LLM-quality claim. No commit or push.
