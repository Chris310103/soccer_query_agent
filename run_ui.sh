#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo "Missing .venv in project root."
  exit 1
fi

source .venv/bin/activate

if [ ! -d "soccer-query-ui" ]; then
  echo "Missing soccer-query-ui frontend directory."
  exit 1
fi

if [ ! -d "soccer-query-ui/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd soccer-query-ui && npm install)
fi

uvicorn soccer_agent.api.app:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

(cd soccer-query-ui && npm run dev -- --host 127.0.0.1 --port 5174) &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

sleep 3
open http://127.0.0.1:5174 || true

wait