#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PORT=${QG_UI_PORT-8501}
if [[ ! "$PORT" =~ ^[0-9]{1,5}$ ]] || (( 10#$PORT < 1 || 10#$PORT > 65535 )); then
  printf '%s\n' 'QG_UI_PORT must be an integer between 1 and 65535' >&2
  exit 2
fi
PORT=$((10#$PORT))
PY=.venv/Scripts/python.exe
[[ -f "$PY" ]] || PY=.venv/bin/python
exec "$PY" -m streamlit run workspace.py --server.address 127.0.0.1 --server.port "$PORT" --browser.gatherUsageStats false
