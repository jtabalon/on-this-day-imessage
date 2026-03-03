#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Create virtualenv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Install dependencies
echo "Installing dependencies..."
.venv/bin/pip install -q -r requirements.txt

# Start the server and open the browser
echo "Starting server at http://127.0.0.1:8000"
open "http://127.0.0.1:8000" 2>/dev/null || true
exec .venv/bin/python run.py
