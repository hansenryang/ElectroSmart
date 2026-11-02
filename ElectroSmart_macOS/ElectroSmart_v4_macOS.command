#!/bin/zsh
set -e
cd "$(dirname "$0")"
echo "ElectroSmart Qt-only · (Rb | Qb) + (Ri | Qi) + Qt"
PORT="${ELECTROSMART_PORT:-8502}"
REUSE_PY="$PWD/../../ElectroSmart-try-ECM-fitting/ElectroSmart_macOS/ElectroSmartEnv/bin/python"
if [ -x "$PWD/ElectroSmartEnv/bin/python" ]; then
  PY="$PWD/ElectroSmartEnv/bin/python"
elif [ -x "$REUSE_PY" ]; then
  PY="$REUSE_PY"
else
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Python 3.11 or newer is required."; exit 1; }
  python3 -m venv ElectroSmartEnv
  PY="$PWD/ElectroSmartEnv/bin/python"
  "$PY" -m pip install -r requirements.txt
fi
"$PY" -c 'import streamlit, pandas, numpy, matplotlib, scipy, galvani, openpyxl, PIL'
exec "$PY" -m streamlit run app.py --server.address 127.0.0.1 --server.port "$PORT" --browser.gatherUsageStats false
