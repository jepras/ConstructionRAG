#!/bin/bash

# Local development startup script with local indexing container
# This script starts the full stack: ngrok, backend, and local indexing container

set -e  # Exit on any error

echo "🚀 Starting local development environment with local indexing..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ Error: ngrok is not installed"
    echo "Install with: brew install ngrok"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed"
    echo "Install with: brew install jq"
    exit 1
fi

# Check if local Supabase is running
echo "🔍 Checking if local Supabase is running..."
if ! curl -s http://localhost:54321/health > /dev/null; then
    echo "❌ Local Supabase is not running on port 54321"
    echo "Start it with: supabase start"
    exit 1
fi
echo "✅ Local Supabase is running"

# Start dual ngrok tunnels in the background
echo "📡 Starting ngrok tunnel for backend on port 8000..."
ngrok http 8000 --log=stdout > ngrok_backend.log 2>&1 &
NGROK_BACKEND_PID=$!

echo "📡 Starting ngrok tunnel for storage on port 54321..."
ngrok http 54321 --log=stdout > ngrok_storage.log 2>&1 &
NGROK_STORAGE_PID=$!

# Wait for ngrok to start up
echo "⏳ Waiting for ngrok tunnels to initialize..."
sleep 8

# Get both public URLs from ngrok API
echo "🔍 Fetching ngrok tunnel URLs..."
NGROK_BACKEND_URL=""
NGROK_STORAGE_URL=""

for i in {1..15}; do
    # Check both ngrok API endpoints (4040 and 4041) since each process starts its own interface
    for port in 4040 4041; do
        TUNNELS=$(curl -s localhost:$port/api/tunnels 2>/dev/null || echo "")

        if [[ -n "$TUNNELS" && "$TUNNELS" != "null" ]]; then
            # Extract backend URL (port 8000)
            if [[ -z "$NGROK_BACKEND_URL" ]]; then
                NGROK_BACKEND_URL=$(echo "$TUNNELS" | jq -r '.tunnels[]? | select(.config.addr=="http://localhost:8000") | .public_url' 2>/dev/null || echo "")
            fi

            # Extract storage URL (port 54321)
            if [[ -z "$NGROK_STORAGE_URL" ]]; then
                NGROK_STORAGE_URL=$(echo "$TUNNELS" | jq -r '.tunnels[]? | select(.config.addr=="http://localhost:54321") | .public_url' 2>/dev/null || echo "")
            fi
        fi
    done

    # Check if we have both URLs
    if [[ -n "$NGROK_BACKEND_URL" && "$NGROK_BACKEND_URL" != "null" && -n "$NGROK_STORAGE_URL" && "$NGROK_STORAGE_URL" != "null" ]]; then
        break
    fi

    echo "Attempt $i/15: Waiting for ngrok tunnels..."
    sleep 2
done

# Validate we got both URLs
if [[ -z "$NGROK_BACKEND_URL" || "$NGROK_BACKEND_URL" == "null" ]]; then
    echo "❌ Failed to get backend ngrok URL after 15 attempts"
    echo "Check ngrok_backend.log for details:"
    cat ngrok_backend.log
    kill $NGROK_BACKEND_PID $NGROK_STORAGE_PID 2>/dev/null || true
    exit 1
fi

if [[ -z "$NGROK_STORAGE_URL" || "$NGROK_STORAGE_URL" == "null" ]]; then
    echo "❌ Failed to get storage ngrok URL after 15 attempts"
    echo "Check ngrok_storage.log for details:"
    cat ngrok_storage.log
    kill $NGROK_BACKEND_PID $NGROK_STORAGE_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Backend ngrok tunnel ready: $NGROK_BACKEND_URL"
echo "✅ Storage ngrok tunnel ready: $NGROK_STORAGE_URL"
echo "🌐 Ngrok web interface: http://localhost:4040"

# Update .env.indexing with your actual API keys
echo "📝 Checking .env.indexing configuration..."
if [[ -f .env.indexing ]]; then
    if grep -q "your_.*_api_key_here" .env.indexing; then
        echo "⚠️  WARNING: Please update .env.indexing with your actual API keys:"
        echo "   - VOYAGE_API_KEY"
        echo "   - OPENROUTER_API_KEY"
        echo ""
        echo "You can copy these from your Beam environment or backend/.env"
        echo ""
        read -p "Press Enter to continue anyway, or Ctrl+C to exit and update keys..."
    fi
else
    echo "❌ .env.indexing file not found"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    if [[ -n "$NGROK_BACKEND_PID" ]]; then
        kill $NGROK_BACKEND_PID 2>/dev/null || true
        echo "🔴 Stopped backend ngrok tunnel"
    fi
    if [[ -n "$NGROK_STORAGE_PID" ]]; then
        kill $NGROK_STORAGE_PID 2>/dev/null || true
        echo "🔴 Stopped storage ngrok tunnel"
    fi
    echo "🛑 Stopping docker containers..."
    docker-compose down
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

echo "📦 Starting backend and indexing containers with docker-compose..."
echo "Press Ctrl+C to stop everything"
echo ""
echo "🔗 Services will be available at:"
echo "   - Backend API: http://localhost:8000"
echo "   - Indexing API: http://localhost:8001"
echo "   - Webhook endpoint: $NGROK_BACKEND_URL/api/wiki/internal/webhook"
echo "   - Storage tunnel (for VLM): $NGROK_STORAGE_URL"
echo "   - Local Supabase Studio: http://127.0.0.1:54323"
echo ""

# Start docker-compose with both environment variables
BACKEND_API_URL=$NGROK_BACKEND_URL \
NGROK_STORAGE_URL=$NGROK_STORAGE_URL \
docker-compose up backend indexing