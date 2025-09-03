# PDF Highlighting Implementation Plan

## Current Status (Updated: 2025-01-03)
- ✅ **COMPLETE**: Bbox data is now extracted AND preserved through entire pipeline
- ✅ **VERIFIED**: Test PDF shows 100% bbox preservation rate 
- ✅ Frontend has placeholder for PDF viewer in SourcePanel.tsx
- ⏳ Ready for Phase 2: PDF Viewer Integration

## Phase 1: Preserve Bbox Data ✅ COMPLETED

### Changes Implemented

#### 1.1 PartitionStep (`backend/src/pipeline/indexing/steps/partition.py`)
**✅ PyMuPDF Path (line 1428)**:
- Added `"bbox": block_bbox` to metadata dictionary
- Extracts bbox as tuple: `(x0, y0, x1, y1)` in points

**✅ Unstructured Path (line 209)**:
- Added `coordinates=True` parameter to `partition_pdf()`
- Extracts bbox from element.metadata.coordinates.points (lines 240-245)
- Converts from points array to bbox format

**✅ Critical Fix (line 1096)**:
- Added "bbox" to `essential_fields` in `_clean_metadata()` function
- This was the key blocker - metadata was being stripped out

#### 1.2 MetadataStep (`backend/src/pipeline/indexing/steps/metadata.py`)
**✅ Text Elements (line 97)**:
- Added `"bbox": metadata_dict.get("bbox")` to structural_metadata

**✅ Table Elements (line 139)**:
- Added `"bbox": metadata_dict.get("bbox")` to structural_metadata

#### 1.3 ChunkingStep (`backend/src/pipeline/indexing/steps/chunking.py`)
**✅ Chunk Metadata (line 706)**:
- Added `"bbox": meta.get("bbox")` to preserve bbox in final chunks

### 1.4 Testing & Verification ✅ VERIFIED

**Test Results**:
- ✅ PyMuPDF extracts bbox correctly as tuples: `(x0, y0, x1, y1)`
- ✅ 100% of text elements have bbox after PartitionStep
- ✅ Bbox survives metadata cleaning (added to essential_fields)
- ✅ Tuples serialize correctly to JSON as arrays

**Verification Scripts Created**:
- `test_bbox_full_flow.py` - Tests complete partition flow
- `debug_bbox_extraction.py` - Debug bbox at each step
- `verify_bbox.py` - Check database after indexing

```python
# Script to verify bbox in chunks after re-indexing
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()
db = create_client(url, key)

# Check chunks for bbox
result = db.table('document_chunks').select('metadata').eq('indexing_run_id', 'YOUR_RUN_ID').limit(5).execute()
for chunk in result.data:
    meta = json.loads(chunk['metadata']) if isinstance(chunk['metadata'], str) else chunk['metadata']
    if 'bbox' in meta:
        print(f"✅ Found bbox: {meta['bbox']}")
    else:
        print("❌ No bbox found")
```

## Phase 2: PDF Viewer Integration (Future)

### Technology Choice
**Recommended**: react-pdf (client-side rendering)
- Package: `@react-pdf/renderer` or `react-pdf`
- Lightweight, good React integration
- Can overlay highlights using absolute positioning

### Required Components
1. **PDF serving endpoint**: `/api/documents/{doc_id}/pdf`
2. **PDFViewer component** with:
   - PDF rendering
   - Highlight overlay based on bbox coordinates
   - Page navigation
   - Zoom controls

### Coordinate System Mapping
- PyMuPDF bbox: `(x0, y0, x1, y1)` in points (72 DPI)
- Need to scale to PDF viewer coordinates
- Consider page rotation and different viewport sizes

## Phase 3: Query Integration (Future)

### Data Flow
```
User Query
    ↓
Retrieved Chunks (with bbox & page_number)
    ↓
Query Response Component
    ↓
SourcePanel (with PDF viewer)
    ↓
Highlighted regions on PDF
```

### API Response Enhancement
Modify query response to include:
```json
{
  "sources": [
    {
      "chunk_id": "...",
      "document_id": "...",
      "filename": "...",
      "page_number": 5,
      "bbox": [100, 200, 300, 400],
      "content": "..."
    }
  ]
}
```

## Implementation Checklist

### Phase 1 ✅ COMPLETED
- [x] Modify partition.py to preserve bbox
- [x] Add bbox to essential_fields in _clean_metadata
- [x] Test with single document locally
- [x] Verify bbox extraction (100% success rate)
- [x] Ensure bbox survives through all pipeline steps

### Phase 2 (Next)
- [ ] Add PDF serving endpoint
- [ ] Install react-pdf
- [ ] Create PDFViewer component
- [ ] Implement highlight overlay
- [ ] Test with sample bbox coordinates

### Phase 3 (Later)
- [ ] Connect query results to PDF viewer
- [ ] Implement click-to-scroll to source
- [ ] Add multi-page highlight support
- [ ] Optimize performance for large PDFs

## Notes
- Bbox coordinates from PyMuPDF are in points (1/72 inch)
- Consider storing page dimensions for proper scaling
- May need to handle rotated pages
- Table and image elements already have bbox (lines 1303, 1331 in partition.py)