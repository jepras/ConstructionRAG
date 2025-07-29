# Project Memories

## Database Configuration
- The project uses production Supabase database, not local development setup
- Database migrations are applied directly to production
- Environment configuration is handled via .env files with production database credentials
- Previous database migrations have been successfully applied to production

## User Preferences
- The user prefers to install Python packages using the project's root virtual environment
- The user prefers that the assistant never touch their .env files
- The project uses FastAPI background tasks instead of Celery workers for background processing
- The user prefers that VLM prompts remain in English, and the language of the caption output should be determined by a variable defined at the top of the file
- The user prefers to avoid hardcoded language-specific term lists and instead use GPT-based semantic query expansion and metadata-driven routing to keep the query processing system language-agnostic 