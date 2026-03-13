#!/usr/bin/env bash
# File Guide: scripts/start_dev.sh
# - Purpose: Quick local Linux/macOS startup script with virtualenv bootstrapping.
# - Usage: bash scripts/start_dev.sh [port]
set -euo pipefail
PORT="${1:-8000}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
