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

# Start ngrok in the background
echo "📡 Starting ngrok tunnel on port 8000..."
ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start up
echo "⏳ Waiting for ngrok to initialize..."
sleep 5

# Get the public URL from ngrok API
echo "🔍 Fetching ngrok tunnel URL..."
NGROK_URL=""
for i in {1..10}; do
    NGROK_URL=$(curl -s localhost:4040/api/tunnels 2>/dev/null | jq -r '.tunnels[]? | select(.proto=="https") | .public_url' 2>/dev/null || echo "")
    if [[ -n "$NGROK_URL" && "$NGROK_URL" != "null" ]]; then
        break
    fi
    echo "Attempt $i/10: Waiting for ngrok..."
    sleep 2
done

if [[ -z "$NGROK_URL" || "$NGROK_URL" == "null" ]]; then
    echo "❌ Failed to get ngrok URL after 10 attempts"
    echo "Check ngrok.log for details:"
    cat ngrok.log
    kill $NGROK_PID 2>/dev/null || true
    exit 1
fi

echo "✅ Ngrok tunnel ready: $NGROK_URL"
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
    if [[ -n "$NGROK_PID" ]]; then
        kill $NGROK_PID 2>/dev/null || true
        echo "🔴 Stopped ngrok tunnel"
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
echo "   - Webhook endpoint: $NGROK_URL/api/wiki/internal/webhook"
echo "   - Local Supabase Studio: http://127.0.0.1:54323"
echo ""

# Start docker-compose with the updated environment
BACKEND_API_URL=$NGROK_URL docker-compose up backend indexing