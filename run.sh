#!/usr/bin/env bash
# One command to start everything: ./run.sh   then open http://127.0.0.1:8010
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ -f .env ] || cp .env.example .env
command -v ffmpeg >/dev/null || { echo "ffmpeg is required (sudo apt install ffmpeg)"; exit 1; }
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8010}"
