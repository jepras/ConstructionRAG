#!/bin/bash

echo "=== DEBUG INFO ==="
echo "Script started at: $(date)"
echo "Current directory: $(pwd)"
echo "Script path: $0"
echo "User: $(whoami)"
echo ""

echo "Environment variables:"
echo "PORT='$PORT'"
echo "PORT length: ${#PORT}"
echo "All env vars containing 'PORT':"
env | grep -i port || echo "No PORT-related env vars found"
echo ""

echo "File system check:"
ls -la
echo ""

# Set default port if not provided
PORT=${PORT:-8000}
echo "Final PORT value: '$PORT'"
echo "Final PORT type: $(echo $PORT | wc -c) characters"

echo "Starting ConstructionRAG API on port $PORT"
echo "Command: uvicorn src.main:app --host 0.0.0.0 --port $PORT"
echo "=================="

# Start the application
exec uvicorn src.main:app --host 0.0.0.0 --port $PORT 