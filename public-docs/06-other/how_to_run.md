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


#### Test query for retrieval system 
python -c "
import asyncio
import sys
sys.path.append('.')
from tests.integration.test_danish_query_baseline import run_query_with_indexing_run

async def run_multiple():
    queries = [
        'adgangskontrol anlæg el sikring',
        'adk aia',
        'ventilation hvac varme brugsvand afløbsrør',
        'belysning hovedledning  føringsveje tavler?',
        'Hvad handler elenterprisen om?',
        'Hvad er kravene til sikkerhed og låse?'
    ]

    run_id = 'b1aa2098-d307-4cbf-94fb-e894c5739222'

    for query in queries:
        print(f'\n--- Running: {query} ---')
        await run_query_with_indexing_run(query, run_id)

asyncio.run(run_multiple())
"






?

python -c "
import asyncio
import sys
sys.path.append('.')
from tests.integration.test_danish_query_baseline import run_query_with_indexing_run

async def run_multiple():
    queries = [
        'byggeprojekt omfang målsætninger mål leverancer?',
        'Hvad handler bygge projektet om?',
        'Hvilke leverancer er der i projektet?',
        'Hvad er opgavens omfang?',
        'installation krav fag teknisk beskrivelse',
        'opgave formål'
    ]

    run_id = 'b1aa2098-d307-4cbf-94fb-e894c5739222'

    for query in queries:
        print(f'\n--- Running: {query} ---')
        await run_query_with_indexing_run(query, run_id)

asyncio.run(run_multiple())
"

curl -X POST http://localhost:8000/api/wiki/runs \
    -H "Content-Type: application/json" \
    -d '{"indexing_run_id": "b1aa2098-d307-4cbf-94fb-e894c5739222"}'

curl -X POST "http://localhost:8000/api/wiki/runs?index_run_id=b1aa2098-d307-4cbf-94fb-e894c5739222" \
        -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6IkFDMkJFbCtEWkxJeDNzb3QiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2x2dnlremRkYnlyeGN4Z2lhaHVvLnN1cG
      FiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJhNGJlOTM1ZC1kZDE3LTRkYjItYWE0ZS1iNDk4OTI3N2JiMWEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU2OTk4NzkyLCJpYXQiOjE3NTY5OTU
      xOTIsImVtYWlsIjoiamVwcmFzaGVyQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRh
      dGEiOnsiZW1haWwiOiJqZXByYXNoZXJAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYTRiZTkzNWQtZGQxNy00ZGIyLWFhNGUtYjQ5O
      DkyNzdiYjFhIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3NTY5OTUxOTJ9XSwic2Vzc2lvbl9pZCI6Im
      VlYzAxYzIwLTJlNWEtNDBiOC04NzkzLTQzN2I5MzlmYTM3YiIsImlzX2Fub255bW91cyI6ZmFsc2V9.j0G_La0MTX2uz0PcaS7dA-tPAUHPoezMjYMVLZiFUsY")


curl -X POST "https://localhost:8000/api/uploads" \
    -H "Content-Type: multipart/form-data" \
    -F "files=@/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/data/external/construction_pdfs/smallest-doc.pdf" \
    -F "email=test-config-flow@example.com"

    
curl -X POST "http://localhost:8000/api/wiki/runs?index_run_id=d5fa952a-4a67-4413-aebc-daad6eac7a68"


curl -X POST "http://localhost:8000/api/wiki/runs?index_run_id=fdf37869-4ba6-4743-b73e-1587af8d6e1b" \
        -H "Content-Type: application/json" \
        -v
