#!/usr/bin/env python3
"""Quick test script for PDF validation service."""

import asyncio
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.pdf_validation_service import PDFValidationService


async def test_validation():
    """Test the PDF validation service with a simple PDF."""
    
    # Create a minimal valid PDF
    minimal_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000203 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
293
%%EOF"""
    
    # Test with suspicious PDF (contains JavaScript)
    suspicious_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R /OpenAction << /S /JavaScript /JS (alert('test')) >> >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000108 00000 n
0000000165 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
237
%%EOF"""
    
    validator = PDFValidationService()
    
    print("Testing valid PDF...")
    result1 = await validator.validate_pdf(minimal_pdf, "test.pdf", is_authenticated=False)
    print(f"  Valid: {result1['is_valid']}")
    print(f"  Pages: {result1.get('metadata', {}).get('page_count', 'Unknown')}")
    print(f"  Errors: {result1.get('errors', [])}")
    print(f"  Security: {result1.get('security', {})}")
    print()
    
    print("Testing suspicious PDF with JavaScript...")
    result2 = await validator.validate_pdf(suspicious_pdf, "suspicious.pdf", is_authenticated=False)
    print(f"  Valid: {result2['is_valid']}")
    print(f"  Errors: {result2.get('errors', [])}")
    print(f"  Security: {result2.get('security', {})}")
    print()
    
    print("Testing batch validation...")
    batch_result = await validator.validate_batch(
        [("test1.pdf", minimal_pdf), ("test2.pdf", minimal_pdf)],
        is_authenticated=False
    )
    print(f"  Overall valid: {batch_result['is_valid']}")
    print(f"  Total pages: {batch_result['total_pages']}")
    print(f"  Processing time estimate: {batch_result.get('total_processing_time_minutes', 0)} minutes")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_validation())