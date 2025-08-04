#!/bin/bash
# Setup test environment for PDF processing comparison

echo "🚀 Setting up test environment for PDF processing comparison..."

# Create test-specific virtual environment
python -m venv test_venv
source test_venv/bin/activate

echo "📦 Installing base dependencies..."
pip install --upgrade pip

# Install core dependencies (lightweight)
pip install python-dotenv
pip install PyMuPDF  # fitz
pip install requests

echo "📦 Installing unstructured with minimal dependencies..."
# Install unstructured with only PDF support to minimize conflicts
pip install "unstructured[pdf]"

# Optional: Install additional OCR dependencies if needed
# pip install tesseract
# pip install "unstructured[all-docs]"  # Only if you need full support

echo "✅ Test environment ready!"
echo "To activate: source notebooks/01_partition/test_venv/bin/activate"
echo "To run comparison: python notebooks/01_partition/pdf_strategy_comparison.py"
echo "To deactivate: deactivate"