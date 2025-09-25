#!/bin/bash
# This script starts the QuickSave application in development mode.
# It first ensures all dependencies are installed, then starts the server.
#
# You can pass a port number as an argument to this script.
# If no port is provided, it defaults to 8888.
#
# Example usage:
# ./run_dev.sh
# ./run_dev.sh 8000

# --- Dependency Installation ---
echo "Checking and installing dependencies..."
pip install -r quicksave/app/requirements.txt
echo "Dependencies are up to date."
echo ""

# --- Port Configuration ---
export PORT=${1:-8888}
echo "Starting QuickSave on port $PORT"

# --- Server Execution ---
# We run uvicorn directly and point it to the 'app' instance in 'quicksave.app.main'.
# This is the standard way to run uvicorn and ensures the reloader works correctly.
# We use a custom log configuration to ensure all log messages have a timestamp.
uvicorn quicksave.app.main:app --reload --port $PORT --host 0.0.0.0 --log-config quicksave/app/log_config.yaml