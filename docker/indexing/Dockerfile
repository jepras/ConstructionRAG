# Dockerfile for local indexing container
# Mirrors exact Beam configuration from beam-app.py

FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies - EXACT copy from beam-app.py commands
RUN apt-get update && \
    # Install core system dependencies (libgl1-mesa-glx replaced with libgl1 in newer Debian)
    apt-get install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libxrender1 libgomp1 && \
    # Install additional runtime libraries 
    apt-get install -y libgcc-s1 libstdc++6 fonts-liberation && \
    # Install OCR and PDF processing tools
    apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-dan tesseract-ocr-eng && \
    # Install additional image processing dependencies
    apt-get install -y libjpeg-dev libpng-dev libtiff-dev libwebp-dev && \
    # Clean up
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # Verify installations
    tesseract --version && pdfinfo -v || echo 'Warning: Some dependencies may not be properly installed'

# Copy requirements files
COPY backend/beam_requirements.txt .
COPY docker/indexing/requirements-local.txt .

# Install Python dependencies - EXACT copy from beam_requirements.txt
RUN pip install --no-cache-dir -r beam_requirements.txt

# Install additional dependencies needed for local HTTP wrapper
RUN pip install --no-cache-dir -r requirements-local.txt

# Copy static files that change rarely (for initial build)
# Note: In development, these will be volume-mounted for hot reloading
COPY backend/src/ ./src/
COPY backend/beam-app.py ./beam_app.py
COPY docker/indexing/entrypoint.py ./

# Set environment variables for conservative resource usage
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Conservative resource limits for 8GB machine
ENV MAX_WORKERS=1
ENV MEMORY_LIMIT=4096
ENV CHUNK_SIZE=500

# Expose port for internal API
EXPOSE 8001

# Run the indexing service
CMD ["python", "entrypoint.py"]