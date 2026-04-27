#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-venv}"
PYTHON_BIN="$ROOT_DIR/$VENV_DIR/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Virtual environment not found: $VENV_DIR" >&2
  echo "Run ./install.sh first." >&2
  exit 1
fi

set +e
"$PYTHON_BIN" configure.py "$@"
status=$?
set -e

if [ "$status" -eq 42 ]; then
  exec "$PYTHON_BIN" main.py
fi

exit "$status"
