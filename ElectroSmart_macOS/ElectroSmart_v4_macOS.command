#!/bin/zsh
set -e

cd "$(dirname "$0")"

echo "================================"
echo "ElectroSmart v4.6 for macOS"
echo "================================"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  echo "ERROR: python3 was not found."
  echo "Install Python 3.11 or newer from https://www.python.org/downloads/macos/"
  read "unused?Press Return to close..."
  exit 1
fi

echo
echo "[1/3] Checking virtual environment..."
if ! "$PYTHON_CMD" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "ERROR: ElectroSmart requires Python 3.11 or newer."
  read "unused?Press Return to close..."
  exit 1
fi
if [ ! -x "ElectroSmartEnv/bin/python" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_CMD" -m venv ElectroSmartEnv
fi

PY="$PWD/ElectroSmartEnv/bin/python"

echo
echo "[2/3] Installing/updating dependencies..."
"$PY" -m pip install -r requirements.txt

echo
echo "[3/3] Launching ElectroSmart v4.6..."
"$PY" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false

echo
echo "ElectroSmart closed."
read "unused?Press Return to close..."
