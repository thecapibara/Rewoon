#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
STAMP_FILE="$VENV_DIR/.req_installed"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv "$VENV_DIR"
fi

if [ ! -f "$STAMP_FILE" ] || [ "$REQ_FILE" -nt "$STAMP_FILE" ]; then
    echo "Installing dependencies..."
    "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
    "$VENV_DIR/bin/pip" install -r "$REQ_FILE"
    touch "$STAMP_FILE"
fi

echo "Starting Rewoon..."
exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/rewoon.py" "$@"
