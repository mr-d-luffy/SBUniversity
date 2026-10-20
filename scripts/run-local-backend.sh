#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SERVER_DIR="$REPO_ROOT/server"
PYTHON="$SERVER_DIR/.venv/bin/python"
PORT="${SBUNIVERSITY_API_PORT:-8010}"

if [ ! -x "$PYTHON" ]; then
  printf 'SiliconBrains University virtualenv not found at %s\n' "$PYTHON" >&2
  printf 'Create it and install server dependencies before starting the API.\n' >&2
  exit 1
fi

cd "$SERVER_DIR"
exec "$PYTHON" -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "$PORT" \
  --reload
