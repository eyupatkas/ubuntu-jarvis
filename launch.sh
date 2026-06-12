#!/bin/bash
# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Launch main.py using virtual environment python
export MATRIX_RAIN="true"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python3 main.py
else
    python3 main.py
fi
