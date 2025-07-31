# Optimized Docker build with better layer caching
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies first (these change rarely)
# Group apt commands to reduce layers
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
# This layer will be cached unless requirements.txt changes
COPY requirements.txt .

# Install Python dependencies with optimized caching
# Use --no-cache-dir to avoid pip cache issues, but leverage Docker layer caching
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code (this layer changes most frequently)
# Copy in order of least to most frequently changing files
COPY config/ ./config/
COPY start.sh ./start.sh
COPY src/ ./src/

# Create non-root user for security (this layer rarely changes)
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
RUN chmod +x start.sh
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["./start.sh"] 