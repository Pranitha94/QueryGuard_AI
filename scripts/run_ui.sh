#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
[[ -f "$PY" ]] || PY=.venv/bin/python
exec "$PY" -m streamlit run workspace.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
