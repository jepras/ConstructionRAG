# How to run

## For local development
### Backend
# From project root
supabase start 
(if not started already)

./start-local-dev-with-indexing.sh

Flow:
1. Prerequisites Check: Validates ngrok, jq, and local Supabase are available
2. Ngrok Setup: Creates public tunnel on port 8000 for webhook testing
3. Environment Setup: Sets BACKEND_API_URL to ngrok URL for webhook callbacks
4. Docker Launch: Starts both backend and indexing services via docker-compose

Key Features:
- Public webhook endpoint: Beam can call back to {ngrok_url}/api/wiki/internal/webhook
- Local isolation: Uses local Supabase database (port 54321)

### Frontend
# From project root (in a new terminal)
source venv/bin/activate
cd frontend
or 
npm run dev

## Pre production
- Make sure Docker is running
docker-compose up --build
 (in root (runs both frontend & backend))

## Production
- Push to git. Both Streamlit & Railway gets updated. 

## Tests
Run from root: 

### Indexing pipeline integration test
python backend/tests/integration/test_pipeline_integration.py

### Beam deploy command
cd backend && 
beam deploy beam-app.py:process_documents

### 
supabase db push

