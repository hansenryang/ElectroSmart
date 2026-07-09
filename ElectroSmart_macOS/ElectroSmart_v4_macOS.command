#!/bin/zsh
set -e

cd "$(dirname "$0")"

echo "================================"
echo "ElectroSmart v4 for macOS"
echo "================================"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  echo "ERROR: python3 was not found."
  echo "Install Python 3.9 or newer from https://www.python.org/downloads/macos/"
  read "unused?Press Return to close..."
  exit 1
fi

echo
echo "[1/3] Checking virtual environment..."
if [ ! -x "ElectroSmartEnv/bin/python" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_CMD" -m venv ElectroSmartEnv
fi

PY="$PWD/ElectroSmartEnv/bin/python"

echo
echo "[2/3] Installing/updating dependencies..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt

echo
echo "[3/3] Launching ElectroSmart v4..."
"$PY" -m streamlit run app.py

echo
echo "ElectroSmart closed."
read "unused?Press Return to close..."
