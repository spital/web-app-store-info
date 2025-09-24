#!/bin/bash
# This script starts the QuickSave application in development mode.
# It changes to the 'quicksave' directory and then runs the Python application.
#
# You can pass a port number as an argument to this script.
# If no port is provided, it defaults to 8888.
#
# Example usage:
# ./run_dev.sh
# ./run_dev.sh 8000

export PORT=$1

if [ -z "$PORT" ]; then
  echo "Starting QuickSave on default port (8888)"
  PORT=8888
else
  echo "Starting QuickSave on port $PORT"
fi

cd quicksave
# The PORT environment variable is already exported, so we can just run the command
python app/main.py