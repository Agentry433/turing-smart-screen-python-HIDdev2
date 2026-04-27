#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-venv}"

echo "turing-smart-screen-python-HIDdev installer"
echo "==========================================="

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN was not found." >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Installing Python requirements..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo
echo "Optional HID permission setup"
echo "-----------------------------"
if [ -f "tools/99-smartmonitor-hiddev.rules" ]; then
  if command -v sudo >/dev/null 2>&1; then
    read -r -p "Install udev rule for SmartMonitor HID access? [y/N] " answer
    case "$answer" in
      [yY]|[yY][eE][sS])
        sudo cp tools/99-smartmonitor-hiddev.rules /etc/udev/rules.d/99-smartmonitor-hiddev.rules
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "udev rule installed. Replug the monitor before running the app."
        ;;
      *)
        echo "Skipped udev rule installation."
        ;;
    esac
  else
    echo "sudo not found; skipping udev rule installation."
  fi
fi

echo
echo "Running doctor..."
"$VENV_DIR/bin/python" tools/smartmonitor-theme-manager.py doctor || true

echo
echo "Install complete."
echo "Start configuration with:"
echo "  ./run-configure.sh"
echo
echo "Start the monitor runtime with:"
echo "  ./run-monitor.sh"
