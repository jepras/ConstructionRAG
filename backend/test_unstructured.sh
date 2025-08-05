#!/bin/bash
# Test script for Unstructured[pdf] in Docker environment

set -e  # Exit on any error

echo "🧪 Testing Unstructured[pdf] with system packages"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "beam_requirements.txt" ]; then
    echo "❌ Error: beam_requirements.txt not found. Please run this from the backend directory."
    exit 1
fi

# Check if test PDF exists
if [ ! -f "../data/external/construction_pdfs/test-with-little-variety.pdf" ]; then
    echo "❌ Error: Test PDF not found. Please ensure the test PDF exists."
    echo "   Expected: ../data/external/construction_pdfs/test-with-little-variety.pdf"
    exit 1
fi

echo "📦 Building Docker image..."
docker build -f Dockerfile.test_unstructured -t test-unstructured .

echo ""
echo "🚀 Running Unstructured test..."
echo "=================================================="

# Run the container with the data directory mounted
docker run --rm \
    -v "$(pwd)/../data:/app/data" \
    test-unstructured

echo ""
echo "✅ Test completed!"
echo ""
echo "If all tests passed, you can now update beam-app.py with confidence."
echo "If tests failed, check the error messages above for missing dependencies." 