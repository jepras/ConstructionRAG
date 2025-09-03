- 

# Config 
Always keep a single source of truth for all configs - besides secrets that should be retrieved from a settings file. Ensure SoT is validated and checked on startup.

# Validation
Use Pydantic's BaseModel for consistent input/output validation and response schemas.

Use Pydantic v2 patterns with ConfigDict & computed_fields. Use modern typing.

Use typed inputs/outputs for important services (especially with LLM steps).

Optimize data serialization and deserialization with Pydantic.

# Linting & preferences
Prefer absolute imports across the codebase. 

# Errors
Use middleware for logging, error monitoring, and performance optimization.

Uniform error surface using AppError hierarchy; no direct HTTPException in app code.
Ensure standard error envelope and request id should be bind to logs.
Only use structlog for logging. 

# API
Keep APIs restful