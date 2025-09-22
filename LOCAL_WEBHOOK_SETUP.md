# Local Webhook Development Setup

This guide helps you test webhook functionality locally using ngrok.

## Prerequisites

```bash
# Install required tools
brew install ngrok jq

# Sign up for ngrok (free tier is fine)
# Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

## Usage

### Quick Start
```bash
# Instead of: docker-compose up backend
# Use this single command:
./start-local-dev.sh
```

### What the script does:
1. ✅ Starts ngrok tunnel on port 8000
2. ✅ Gets the public HTTPS URL (e.g., `https://abc123.ngrok.io`) 
3. ✅ Sets `BACKEND_API_URL` environment variable
4. ✅ Starts your backend with docker-compose
5. ✅ Shows webhook endpoint URL for testing

### Example output:
```
🚀 Starting local development environment with webhook support...
📡 Starting ngrok tunnel on port 8000...
⏳ Waiting for ngrok to initialize...
🔍 Fetching ngrok tunnel URL...
✅ Ngrok tunnel ready: https://abc123-def456.ngrok.io
🌐 Ngrok web interface: http://localhost:4040
📦 Starting backend with docker-compose...

Webhook endpoint available at: https://abc123-def456.ngrok.io/api/wiki/internal/webhook
```

## Testing Webhook Flow

1. **Upload documents** via your local frontend (`http://localhost:3000`)
2. **Beam processes** documents and calls your ngrok webhook URL
3. **Local webhook** receives the call at `/api/wiki/internal/webhook`
4. **Wiki generation** runs locally against your local/staging database

## Monitoring

- **Ngrok web interface**: http://localhost:4040 (see all webhook requests)
- **Backend logs**: In your terminal where the script is running
- **Ngrok logs**: Check `ngrok.log` file if needed

## Cleanup

Press `Ctrl+C` to stop everything. The script automatically:
- Stops the ngrok tunnel
- Removes temporary environment files
- Restores your original configuration

## Alternative: Manual Setup

If you prefer manual control:

```bash
# Terminal 1: Start ngrok
ngrok http 8000

# Terminal 2: Get URL and start backend
NGROK_URL=$(curl -s localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
BACKEND_API_URL=$NGROK_URL docker-compose up backend
```

## Troubleshooting

### "ngrok not found"
```bash
brew install ngrok
```

### "jq not found"  
```bash
brew install jq
```

### "Failed to get ngrok URL"
- Check if ngrok auth token is configured
- Verify port 4040 is available
- Check `ngrok.log` for detailed error messages