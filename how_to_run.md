# How to run

## For local development
### Backend
# From project root
source venv/bin/activate
cd backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

### Frontend
# From project root (in a new terminal)
source venv/bin/activate
cd frontend
streamlit run streamlit_app/main.py --server.port 8501

## Pre production
- Make sure Docker is running
- Run docker-compose up --build in root (runs both frontend & backend)

## Production
- Push to git. Both Streamlit & Railway gets updated. 