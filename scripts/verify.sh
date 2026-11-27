#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
[[ -f "$PY" ]] || PY=.venv/bin/python
EVIDENCE=${QG_EVIDENCE_DIR:-artifacts}
mkdir -p "$EVIDENCE"
"$PY" scripts/bootstrap.py
"$PY" -m ruff check queryguard scripts tests workspace.py
"$PY" -m ruff format --check queryguard scripts tests workspace.py
"$PY" -m compileall -q queryguard scripts workspace.py
"$PY" -m pytest -q --tb=short --junitxml="$EVIDENCE/pytest.xml"
"$PY" scripts/evaluate.py --output-dir "$EVIDENCE"
