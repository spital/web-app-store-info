#!/bin/bash
# This script starts the QuickSave application in development mode.
#
# You can pass a port number as an argument to this script.
# If no port is provided, it defaults to 8888.
#
# Example usage:
# ./run_dev.sh
# ./run_dev.sh 8000

export PORT=${1:-8888}

echo "Starting QuickSave on port $PORT"

# We run uvicorn directly and point it to the 'app' instance in 'quicksave.app.main'.
# This is the standard way to run uvicorn and ensures the reloader works correctly.
uvicorn quicksave.app.main:app --reload --port $PORT --host 0.0.0.0