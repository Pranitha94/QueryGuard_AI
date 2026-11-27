# Clean-clone reproduction: QueryGuard AI 19472ec

## Scope and outcome

Remote clone at detached `19472ece9771c5530439365d57fe95aa6b176f6a` into `D:/Hermes/Pranitha_projects/queryguard-ai/.local/audit/fresh-clone`. No tracked source edited, no commits/pushes. Parent tracked working tree was not modified. All setup used newly generated clone-only secrets, never parent's .env. New venv was created using parent Python 3.10.20 as an interpreter donor only; all subsequent dependency/test/application executions used clone `.venv/Scripts/python.exe`.

A genuinely new PostgreSQL 16 cluster was initialized in clone `.local/audit/pgdata`, bound solely to 127.0.0.1:55434. Initial cluster database enumeration and empty analytics schema are recorded in `empty-cluster-proof.json` and `empty-database-proof.json`. No preseeded DB was reused. After manually creating the dedicated empty queryguard database, unmodified external-DSN bootstrap seeded 48 customers, 12 products, 360 orders, 720 items. Tests and evaluation succeeded. API/UI ran on unused 8002/8503; isolated HTTP checks succeeded. All own services stopped afterward; ports 55434,8002,8503 refused connections; pg_ctl status returned 3 (no server running).

## Commands/results

Run from clone root; `$PY` means clone `.venv/Scripts/python.exe`. Exact validation commands and RCs also in `commands.json`.

- `git clone https://github.com/Pranitha94/QueryGuard_AI.git <clone>` then `git checkout --detach 19472ec`: RC 0.
- `<parent>/.venv/Scripts/python.exe -m venv .venv`: succeeded, new isolated interpreter/site-packages, not copied parent packages.
- `$PY -m pip install --timeout 30 --retries 1 -r requirements.lock.txt`: tool timed out after 420 seconds during package installation; no process remained when checked. No success RC claimed.
- One bounded recovery: `$PY -m pip install --timeout 15 --retries 0 -r requirements.lock.txt`: RC 0. `$PY -m pip check`: RC 0. Installed metadata matches all 61 exact lock pins, zero mismatches (`final-state.json`). Baseline includes Pillow 12.3.0. No independent vulnerability conclusion here.
- `$PY -m pip install --timeout 15 --retries 0 --no-deps .`: RC 1, setuptools package discovery error (below).
- `$PY scripts/bootstrap.py` before clone .env exists: RC 1, safely refuses occupied 55432.
- `initdb.exe -D <clone>/.local/audit/pgdata -U qg_admin --pwfile <temporary clone-only file> --auth-host=scram-sha-256 --auth-local=scram-sha-256 --encoding=UTF8 --locale=C`: RC 0. Password file removed immediately. Config appended loopback/55434/SCRAM. `postgres.exe -D <new-data-dir>` ran foreground inside a persistent background tool session, not a detached pg_ctl child.
- `$PY scripts/bootstrap.py` with generated `QG_ADMIN_DSN`, `QG_DATABASE_DSN`, `QG_READER_PASSWORD` supplied through environment against brand-new cluster: RC 1, missing queryguard database.
- Admin `CREATE DATABASE queryguard` on new cluster, then exact same bootstrap command/environment: RC 0. Empty schema and seeded counts verified via SQL.
- `$PY -m ruff check queryguard scripts tests workspace.py --no-cache`: RC 0.
- `$PY -m ruff format --check queryguard scripts tests workspace.py --no-cache`: RC 0.
- `$PY -m pytest -q --tb=short -p no:cacheprovider --basetemp=<clone>/.local/audit/pytest-tmp --junitxml=<clone>/.local/audit/pytest.xml`: RC 0; **65 passed, one Starlette/httpx deprecation warning, 45.13 seconds**. tests/test_database.py itself reran unmodified bootstrap using supplied new-cluster environment.
- Evaluation: unmodified scripts/evaluate.py main body loaded with runpy, only module ROOT redirected to `.local/audit/evaluation-root`, with identical committed benchmarks/sql copied there. RC 0; baseline 105/105, schema-aware 105/105, adversarial 40/40. This is deliberately not claimed as literal `scripts/evaluate.py` output-path behavior: redirect prevents overwriting tracked committed evidence. Exact code in commands.json/run_validation.py.
- `bash scripts/run_api.sh`: RC 3, bind error 10048 on occupied 8000, despite successful fresh-DB startup verification.
- `bash scripts/run_ui.sh`: RC 1, port 8501 unavailable.
- `$PY .local/audit/http_isolated.py`: RC 0; starts create_app with audit path under audit and uvicorn on8002; Streamlit on8503 with `QG_API_URL=http://127.0.0.1:8002`. Four expected query outcomes, other session history empty, four live schema tables, evaluation200, OpenAPI docs200, UI health200. Both subprocess trees terminated in finally. UI browser interactions not tested by this agent.
- `pg_ctl.exe -D <new-data-dir> -m fast -w stop`: RC 0; subsequent status RC 3. Only new cluster targeted.

## Verified blockers/defects

1. **Native project package cannot be installed.** `pip install --no-deps .` fails: `Multiple top-level packages discovered in a flat-layout: ['sql', 'artifacts', 'queryguard']`. pyproject.toml has no explicit build-system/package discovery. Source-root runtime/test success is not wheel/package success. Package metadata also declares no runtime dependencies, so after discovery is corrected install-alone reproducibility needs its own acceptance test. README's requirements-only setup can run source directly; package failure is an additional requested acceptance probe, not a claim that README promises pip install . .
2. **Native isolated port is not configurable.** scripts/bootstrap.py:27,31,64 hardcode55432. PG_BIN overrides binaries, not port. A second clean clone cannot execute README bootstrap while original demo runs; it safely refuses before touching existing server. Writing an alternative-port .env alone does not change postgres.conf's hardcoded55432 initialization. Environment QG_ADMIN_DSN bypasses cluster initialization entirely.
3. **External first-run DB prerequisite missing.** With QG_ADMIN_DSN supplied on a genuinely new cluster, bootstrap skips lines80-83 database creation and connects directly to absent queryguard at84. Exact failure: `psycopg.OperationalError ... port 55434 ... FATAL: database "queryguard" does not exist`. External mode needs a precreated dedicated database plus QG_READER_PASSWORD; manually creating that empty DB unblocked all subsequent work.
4. **HTTP launch/smoke ports hardcoded.** run_api.sh always8000, run_ui.sh always8501, smoke.py always probes8000/8501. UI itself supports QG_API_URL; shell launch/smoke do not expose analogous options. Literal smoke.py was intentionally NOT run: it would query unrelated running parent services and would not evidence clone success. Custom equivalent probes only targeted8002/8503.
5. **First-run UI evaluation can be historical.** Clean clone ships artifacts/evaluation.json; isolated /evaluation returned200 and generated_at `2026-11-26T15:22:51.394902+00:00`, not the fresh audit run. Correctly document it as committed prior evidence, not evidence produced by this install. Own evaluation report is separate under audit.

## Precise README improvements

- Replace machine-specific cd with a real git clone URL and generic checkout directory; make venv creation an executable required line, not a comment. Keep every pip/pytest invocation bound to that environment.
- Explain requirements-only source execution versus supported installable packaging; do not add pip install . to README until explicit packaging/dependencies/resources are configured and wheel tested outside source cwd.
- Document exclusive default ports and safe refusal. For concurrent native clones expose DB/API/UI port configuration in bootstrap/launch/smoke; until implemented explicitly state no native bootstrap port override exists.
- Add a manual external-cluster recipe: initdb a new dedicated directory, configure loopback/custom port, start it, create dedicated queryguard database, export BOTH QG_ADMIN_DSN and QG_READER_PASSWORD for bootstrap and QG_DATABASE_DSN for runtime. Merely setting .env is not external mode; bootstrap external branch checks process environment. Native no-admin-env branch manages `.local/pgdata`.
- Clarify foreground workaround prerequisites: PostgreSQL data directory must already be initialized before postgres -D; supplied literal main path must be changed to this checkout. Do not imply running foreground command creates a cluster.
- Show direct uvicorn/Streamlit alternate-port commands plus QG_API_URL, and port-aware smoke invocation once implemented.
- Explain verify.sh writes tracked artifacts/pytest.xml and evaluation artifacts; provide configurable evidence directory to support read-only/source-clean audits. Distinguish committed evaluation from a freshly generated report.

## Limits / evidence locations

No Docker attempt necessary after native path succeeded. No paid API, real data, Ollama/model pulls or image downloads. No arbitrary dependency upgrades. No Python3.11 rerun: parent advised preserving baseline and handles newer-runtime security changes independently. No entire verify.sh execution: it overwrites tracked artifacts; constituent lint/format/pytest/evaluation were executed with evidence redirected. No claim of full native-bootstrap default path success because occupied-port safety prevented it; isolated external-mode path was genuinely run end-to-end. No browser journey claim.

Reports/logs/harnesses/new PostgreSQL data reside under clone `.local/audit`; generated clone-only credentials are in gitignored clone `.env`, isolated environment in gitignored `.venv`. Pytest's application emitted default `.local/audit.jsonl`; after test completion it was relocated to `.local/audit/pytest-default-audit.jsonl`. Imports may generate ordinary gitignored __pycache__; no tracked files changed. `git status --short` was empty at completion.
