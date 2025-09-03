#!/usr/bin/env python3
"""Test if tuples can be serialized to JSON properly."""

import json

# Test bbox as tuple (how PyMuPDF returns it)
bbox_tuple = (56.73, 38.79, 541.60, 58.76)

print("Testing Tuple Serialization:")
print("-"*40)
print(f"Original bbox (tuple): {bbox_tuple}")
print(f"Type: {type(bbox_tuple)}")

# Test direct JSON serialization
try:
    json_str = json.dumps(bbox_tuple)
    print(f"\n✅ Direct serialization works: {json_str}")
    
    # Test deserialization
    loaded = json.loads(json_str)
    print(f"Deserialized type: {type(loaded)}")
    print(f"Deserialized value: {loaded}")
except Exception as e:
    print(f"\n❌ Direct serialization failed: {e}")

# Test in metadata dict
metadata = {
    "page_number": 1,
    "bbox": bbox_tuple,
    "extraction_method": "pymupdf"
}

print("\n\nTesting Metadata Dict Serialization:")
print("-"*40)
print(f"Original metadata: {metadata}")

try:
    json_str = json.dumps(metadata)
    print(f"\n✅ Metadata serialization works")
    print(f"JSON string: {json_str}")
    
    # Test deserialization
    loaded = json.loads(json_str)
    print(f"\nDeserialized metadata: {loaded}")
    print(f"Bbox in deserialized: {loaded.get('bbox')}")
    print(f"Bbox type after deserialize: {type(loaded.get('bbox'))}")
except Exception as e:
    print(f"\n❌ Metadata serialization failed: {e}")

# Test with None value (what might be happening)
print("\n\nTesting None Value:")
print("-"*40)

metadata_with_none = {
    "page_number": 1,
    "bbox": None,
    "extraction_method": "pymupdf"
}

json_str = json.dumps(metadata_with_none)
print(f"Metadata with None bbox: {json_str}")

loaded = json.loads(json_str)
print(f"After deserialize: {loaded}")
print(f"'bbox' in dict: {'bbox' in loaded}")
print(f"bbox value: {loaded.get('bbox')}")

# The issue might be the tuple is getting lost somewhere
print("\n\nPOSSIBLE ISSUE:")
print("-"*40)
print("If bbox starts as a tuple but gets set to None somewhere in the pipeline,")
print("it would serialize as null in JSON, which is what we're seeing in the database.")
print("\nNeed to check where bbox might be getting set to None or not passed through.")