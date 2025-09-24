#!/bin/bash
# This script starts the QuickSave application in development mode.
# It changes to the 'quicksave' directory and then runs the Python application.
#
# You can pass a port number as an argument to this script.
# If no port is provided, the application will use its default (8888).
#
# Example usage:
# ./run_dev.sh
# ./run_dev.sh 8000

# Use provided port or let the application use its default
PORT=$1

if [ -z "$PORT" ]; then
  echo "Starting QuickSave on default port (8888)"
else
  echo "Starting QuickSave on port $PORT"
fi

cd quicksave
PORT=$PORT python app/main.py
