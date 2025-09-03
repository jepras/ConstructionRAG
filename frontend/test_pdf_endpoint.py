import json

# Test script to check if PDF endpoint would work
print("Testing PDF endpoint logic...")

# Simulate the backend logic
def test_pdf_endpoint(document_id, index_run_id=None):
    print(f"Document ID: {document_id}")
    print(f"Index Run ID: {index_run_id}")
    
    # Check what the endpoint would do
    if index_run_id:
        print("Mode: Anonymous access (email upload)")
        print("Would check: indexing_runs table for upload_type='email'")
        print("Would check: indexing_run_documents junction table")
    else:
        print("Mode: Authenticated access")
        print("Would check: documents table with user ownership")
    
    print("\nExpected response if successful:")
    print(json.dumps({
        "url": "signed_url_to_pdf",
        "filename": "document.pdf",
        "expires_in": 3600
    }, indent=2))

# From your screenshot, it looks like you're accessing with an indexing run
test_pdf_endpoint(
    document_id="some-uuid",  # This would come from metadata.document_id
    index_run_id="830e80c5-aa47-4bcb-b21f-3e7e019d5f12"  # From your URL
)
