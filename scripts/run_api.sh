#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
[[ -f "$PY" ]] || PY=.venv/bin/python
exec "$PY" -m uvicorn queryguard.api:app --host 127.0.0.1 --port 8000 --no-access-log
