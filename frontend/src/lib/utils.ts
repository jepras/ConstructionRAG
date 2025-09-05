import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Types for bbox deduplication
interface BboxHighlight {
  bbox: number[];
  chunk_id?: string;
}

// Calculate bbox area
function getBboxArea(bbox: number[]): number {
  const [x0, y0, x1, y1] = bbox;
  return Math.abs(x1 - x0) * Math.abs(y1 - y0);
}

// Calculate intersection area between two bboxes
function getBboxIntersectionArea(bbox1: number[], bbox2: number[]): number {
  const [x0_1, y0_1, x1_1, y1_1] = bbox1;
  const [x0_2, y0_2, x1_2, y1_2] = bbox2;
  
  const xOverlap = Math.max(0, Math.min(x1_1, x1_2) - Math.max(x0_1, x0_2));
  const yOverlap = Math.max(0, Math.min(y1_1, y1_2) - Math.max(y0_1, y0_2));
  
  return xOverlap * yOverlap;
}

// Calculate overlap ratio between two bboxes
function getBboxOverlapRatio(bbox1: number[], bbox2: number[]): number {
  const area1 = getBboxArea(bbox1);
  const area2 = getBboxArea(bbox2);
  const intersectionArea = getBboxIntersectionArea(bbox1, bbox2);
  
  if (area1 === 0 && area2 === 0) return 0;
  
  // Calculate overlap as percentage of the smaller bbox
  const minArea = Math.min(area1, area2);
  return minArea > 0 ? intersectionArea / minArea : 0;
}

// Check if two bboxes are identical (within tolerance)
function areBboxesIdentical(bbox1: number[], bbox2: number[], tolerance: number = 1): boolean {
  if (bbox1.length !== 4 || bbox2.length !== 4) return false;
  
  for (let i = 0; i < 4; i++) {
    if (Math.abs(bbox1[i] - bbox2[i]) > tolerance) {
      return false;
    }
  }
  return true;
}

/**
 * Remove overlapping and duplicate bounding boxes from highlights
 * @param highlights Array of highlights with bbox and chunk_id
 * @param overlapThreshold Minimum overlap ratio to consider bboxes as duplicates (0-1)
 * @param identicalTolerance Tolerance for considering bboxes identical (PDF points)
 * @returns Deduplicated array of highlights
 */
export function deduplicateBboxHighlights(
  highlights: BboxHighlight[], 
  overlapThreshold: number = 0.8,
  identicalTolerance: number = 1
): BboxHighlight[] {
  if (!highlights || highlights.length <= 1) return highlights;
  
  // Filter out invalid bboxes
  const validHighlights = highlights.filter(h => 
    h.bbox && Array.isArray(h.bbox) && h.bbox.length === 4 &&
    h.bbox.every(coord => typeof coord === 'number' && !isNaN(coord))
  );
  
  if (validHighlights.length <= 1) return validHighlights;
  
  const deduplicated: BboxHighlight[] = [];
  const used = new Set<number>();
  
  for (let i = 0; i < validHighlights.length; i++) {
    if (used.has(i)) continue;
    
    const current = validHighlights[i];
    let shouldAdd = true;
    
    // Check against already added highlights
    for (let j = 0; j < deduplicated.length; j++) {
      const existing = deduplicated[j];
      
      // Check if identical
      if (areBboxesIdentical(current.bbox, existing.bbox, identicalTolerance)) {
        shouldAdd = false;
        break;
      }
      
      // Check if significantly overlapping
      const overlapRatio = getBboxOverlapRatio(current.bbox, existing.bbox);
      if (overlapRatio >= overlapThreshold) {
        // Keep the larger bbox (or first one if same size)
        const currentArea = getBboxArea(current.bbox);
        const existingArea = getBboxArea(existing.bbox);
        
        if (currentArea > existingArea) {
          // Replace existing with current
          deduplicated[j] = current;
        }
        shouldAdd = false;
        break;
      }
    }
    
    if (shouldAdd) {
      deduplicated.push(current);
    }
    
    used.add(i);
  }
  
  return deduplicated;
}
