#!/bin/bash

# Local development startup script with ngrok webhook support
# This script starts ngrok, captures the tunnel URL, and starts the backend with proper webhook configuration

set -e  # Exit on any error

echo "🚀 Starting local development environment with webhook support..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ Error: ngrok is not installed"
    echo "Install with: brew install ngrok"
    echo "Or download from: https://ngrok.com/download"
    exit 1
fi

# Check if jq is installed (for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed (needed to parse ngrok API response)"
    echo "Install with: brew install jq"
    exit 1
fi

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

# Update .env file with local development values
echo "📝 Setting up environment variables..."
if [[ -f backend/.env ]]; then
    # Backup existing .env
    cp backend/.env backend/.env.backup
    echo "💾 Backed up existing .env to .env.backup"
    
    # Update the .env file directly with local development values
    sed -i.tmp \
        -e "s|BACKEND_API_URL=.*|BACKEND_API_URL=$NGROK_URL|" \
        -e 's|SUPABASE_URL=.*|SUPABASE_URL="http://host.docker.internal:54321"|' \
        -e 's|SUPABASE_ANON_KEY=.*|SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"|' \
        -e 's|SUPABASE_SERVICE_ROLE_KEY=.*|SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"|' \
        -e "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://localhost:8501,http://localhost:3000,http://localhost:3002,$NGROK_URL|" \
        backend/.env
    rm backend/.env.tmp 2>/dev/null || true
    echo "🔧 Updated .env with local development values (ngrok: $NGROK_URL, supabase: host.docker.internal:54321)"
else
    echo "❌ No backend/.env file found"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    if [[ -n "$NGROK_PID" ]]; then
        kill $NGROK_PID 2>/dev/null || true
        echo "🔴 Stopped ngrok tunnel"
    fi
    if [[ -f backend/.env.backup ]]; then
        mv backend/.env.backup backend/.env
        echo "🔄 Restored original .env"
    fi
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

echo "📦 Starting backend with docker-compose..."
echo "Press Ctrl+C to stop both ngrok and the backend"
echo ""
echo "Webhook endpoint available at: $NGROK_URL/api/wiki/internal/webhook"
echo ""

# Start docker-compose with the updated environment
BACKEND_API_URL=$NGROK_URL docker-compose up backend