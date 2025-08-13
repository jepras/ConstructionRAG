#!/bin/bash

# Kill any process using port 3000
echo "🔍 Checking if port 3000 is in use..."
PID=$(lsof -ti:3000)
if [ ! -z "$PID" ]; then
  echo "⚠️  Port 3000 is in use by process $PID. Killing it..."
  kill -9 $PID
  echo "✅ Process killed successfully"
else
  echo "✅ Port 3000 is available"
fi

# Kill any process using port 8000  
echo "🔍 Checking if port 8000 is in use..."
PID=$(lsof -ti:8000)
if [ ! -z "$PID" ]; then
  echo "⚠️  Port 8000 is in use by process $PID. Killing it..."
  kill -9 $PID
  echo "✅ Process killed successfully"
else
  echo "✅ Port 8000 is available"
fi
