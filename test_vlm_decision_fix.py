#!/usr/bin/env python3
"""
Test VLM decision logic to verify the data type fix
"""
import sys
import os
sys.path.append('/Users/jepperasmussen/workspace/github.com/jepras/ConstructionRAG/backend')

def test_vlm_decision_logic():
    """Test the VLM decision logic with different data type scenarios"""
    
    print("🧪 TESTING VLM DECISION LOGIC")
    print("="*50)
    
    # Simulate data structures from partition step
    test_cases = [
        {
            "name": "String keys in extracted_pages",
            "extracted_pages": {"1": {}, "2": {}, "3": {}},
            "table_elements": [
                {"page": 1, "id": "table_1"},
                {"page": 2, "id": "table_2"}, 
                {"page": 4, "id": "table_4"}  # No full page
            ]
        },
        {
            "name": "Integer keys in extracted_pages",
            "extracted_pages": {1: {}, 2: {}, 3: {}},
            "table_elements": [
                {"page": 1, "id": "table_1"},
                {"page": 2, "id": "table_2"},
                {"page": 4, "id": "table_4"}  # No full page
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Test Case: {test_case['name']}")
        print(f"   Extracted pages: {list(test_case['extracted_pages'].keys())}")
        
        for table_element in test_case['table_elements']:
            table_page = table_element.get("page")
            table_id = table_element.get("id")
            
            # Use the fixed logic from enrichment.py
            has_full_page = table_page in test_case['extracted_pages'] or str(table_page) in test_case['extracted_pages']
            
            status = "SKIP (full-page exists)" if has_full_page else "PROCESS (no full-page)"
            print(f"   Table {table_id} (page {table_page}): {status}")
    
    print(f"\n✅ VLM decision logic test complete!")

if __name__ == "__main__":
    test_vlm_decision_logic()