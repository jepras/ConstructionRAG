'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Set up the worker for react-pdf
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFPageViewerProps {
  pdfUrl: string;
  pageNumber: number;
  highlights?: Array<{
    bbox: number[];
    chunk_id?: string;
  }>;
  scale?: number;
  onPageClick?: () => void;
  className?: string;
}

export default function PDFPageViewerSimple({
  pdfUrl,
  pageNumber,
  highlights = [],
  scale = 1.5,
  onPageClick,
  className = '',
}: PDFPageViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageLoadError, setPageLoadError] = useState<string | null>(null);
  const [documentLoadError, setDocumentLoadError] = useState<string | null>(null);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    console.log('PDFPageViewerSimple: Document loaded with', numPages, 'pages');
    setNumPages(numPages);
    setDocumentLoadError(null);
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('PDFPageViewerSimple: Failed to load document:', error);
    setDocumentLoadError(error.message || 'Failed to load PDF');
  }, []);

  const onPageLoadSuccess = useCallback((page: any) => {
    console.log('PDFPageViewerSimple: Page', pageNumber, 'loaded successfully');
    console.log('PDFPageViewerSimple: Page dimensions:', {
      width: page.width,
      height: page.height,
      originalWidth: page.originalWidth,
      originalHeight: page.originalHeight,
      scale: page.scale,
      rotation: page.rotation,
    });
    setPageLoadError(null);
  }, [pageNumber]);

  const onPageLoadError = useCallback((error: Error) => {
    console.error('PDFPageViewerSimple: Failed to load page:', error);
    setPageLoadError(error.message || 'Failed to load page');
  }, []);

  // Custom text renderer to add highlights
  const textRenderer = useCallback(
    (textItem: any) => {
      if (!highlights || highlights.length === 0) return textItem.str;
      
      // Check if this text item falls within any highlight bbox
      // This is a simplified version - you may need more sophisticated matching
      return textItem.str;
    },
    [highlights]
  );

  // Memoize options to prevent unnecessary reloads
  const documentOptions = useMemo(() => ({
    cMapUrl: 'https://unpkg.com/pdfjs-dist@3.11.174/cmaps/',
    standardFontDataUrl: 'https://unpkg.com/pdfjs-dist@3.11.174/standard_fonts/',
  }), []);

  return (
    <div className={cn('relative overflow-auto bg-gray-50', className)}>
      <Document
        file={pdfUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        onLoadError={onDocumentLoadError}
        loading={
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">Loading PDF...</span>
          </div>
        }
        error={
          <div className="flex flex-col items-center justify-center p-8">
            <AlertCircle className="h-8 w-8 text-destructive mb-2" />
            <p className="text-sm text-destructive">{documentLoadError || 'Failed to load PDF'}</p>
          </div>
        }
        options={documentOptions}
      >
        <div 
          className="relative inline-block"
          onClick={onPageClick}
          style={{ cursor: onPageClick ? 'pointer' : 'default' }}
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            onLoadSuccess={onPageLoadSuccess}
            onLoadError={onPageLoadError}
            renderTextLayer={true}
            renderAnnotationLayer={false}
            customTextRenderer={textRenderer}
            className="shadow-lg"
            error={
              <div className="flex flex-col items-center justify-center p-8 bg-white rounded shadow">
                <AlertCircle className="h-8 w-8 text-destructive mb-2" />
                <p className="text-sm text-destructive">{pageLoadError || 'Failed to load page'}</p>
              </div>
            }
          />
          
          {/* Overlay for highlights */}
          {highlights && highlights.length > 0 && (
            <svg
              className="absolute inset-0 pointer-events-none"
              style={{
                width: '100%',
                height: '100%',
              }}
            >
              {highlights.map((highlight, index) => {
                if (!highlight.bbox || highlight.bbox.length !== 4) return null;
                
                // Debug logging for bbox coordinates
                console.log(`PDFPageViewerSimple: Highlight ${index} bbox:`, {
                  raw: highlight.bbox,
                  scale: scale,
                  chunk_id: highlight.chunk_id,
                });
                
                // Transform bbox coordinates to match the scaled PDF
                // bbox format: [x0, y0, x1, y1] in PDF coordinates (points)
                // Need to scale them based on the current scale factor
                const [x0, y0, x1, y1] = highlight.bbox;
                const scaledX = x0 * scale;
                const scaledY = y0 * scale;
                const scaledWidth = (x1 - x0) * scale;
                const scaledHeight = (y1 - y0) * scale;
                
                console.log(`PDFPageViewerSimple: Highlight ${index} scaled coordinates:`, {
                  x: scaledX,
                  y: scaledY,
                  width: scaledWidth,
                  height: scaledHeight,
                });
                
                return (
                  <rect
                    key={`highlight-${index}`}
                    x={scaledX}
                    y={scaledY}
                    width={scaledWidth}
                    height={scaledHeight}
                    fill="rgba(251, 146, 60, 0.3)"
                    stroke="rgba(251, 146, 60, 0.5)"
                    strokeWidth="1"
                  />
                );
              })}
            </svg>
          )}
        </div>
      </Document>
      
      {/* Page info */}
      {numPages && (
        <div className="absolute bottom-2 right-2 bg-white/90 px-2 py-1 rounded text-xs text-muted-foreground">
          Page {pageNumber} of {numPages}
        </div>
      )}
    </div>
  );
}