FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY start.sh ./start.sh

# Create non-root user for security
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