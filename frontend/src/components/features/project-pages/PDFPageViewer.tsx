'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Loader2, AlertCircle, ZoomIn, ZoomOut } from 'lucide-react';
import { Button } from '@/components/ui/button';

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

export default function PDFPageViewer({
  pdfUrl,
  pageNumber,
  highlights = [],
  scale: initialScale = 1.5,
  onPageClick,
  className = '',
}: PDFPageViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const highlightCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(initialScale);
  const [pageHeight, setPageHeight] = useState<number>(0);

  // Transform bbox coordinates from PDF to canvas
  const transformBboxToCanvas = useCallback(
    (bbox: number[], pageHeight: number, scale: number): [number, number, number, number] => {
      const [x0, y0, x1, y1] = bbox;
      // PDF coordinate system has origin at bottom-left, canvas at top-left
      // So we need to flip the Y coordinates
      const canvasY0 = (pageHeight - y1) * scale;
      const canvasY1 = (pageHeight - y0) * scale;
      const canvasX0 = x0 * scale;
      const canvasX1 = x1 * scale;
      
      return [canvasX0, canvasY0, canvasX1, canvasY1];
    },
    []
  );

  // Draw highlights on the overlay canvas
  const drawHighlights = useCallback(
    (pageHeight: number, scale: number) => {
      const highlightCanvas = highlightCanvasRef.current;
      if (!highlightCanvas || !highlights || highlights.length === 0) return;

      const ctx = highlightCanvas.getContext('2d');
      if (!ctx) return;

      // Clear previous highlights
      ctx.clearRect(0, 0, highlightCanvas.width, highlightCanvas.height);

      // Set highlight style - using primary color with opacity
      ctx.fillStyle = 'rgba(251, 146, 60, 0.3)'; // Orange with 30% opacity

      // Draw each highlight
      highlights.forEach((highlight) => {
        if (!highlight || !highlight.bbox || highlight.bbox.length !== 4) return;
        
        const [x0, y0, x1, y1] = transformBboxToCanvas(highlight.bbox, pageHeight, scale);
        const width = x1 - x0;
        const height = y1 - y0;
        
        ctx.fillRect(x0, y0, width, height);
      });
    },
    [highlights, transformBboxToCanvas]
  );

  // Load and render PDF page
  useEffect(() => {
    console.log('PDFPageViewer: Effect triggered', {
      pdfUrl,
      pageNumber,
      hasHighlights: highlights?.length > 0,
      isServer: typeof window === 'undefined'
    });

    // Only run in browser
    if (typeof window === 'undefined') return;
    
    let cancelled = false;

    const loadPDF = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log('PDFPageViewer: Starting to load PDF from:', pdfUrl);

        // Dynamically import PDF.js
        const pdfjsLib = await import('pdfjs-dist');
        console.log('PDFPageViewer: PDF.js loaded');
        
        // Configure worker
        if (pdfjsLib.GlobalWorkerOptions) {
          pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.js`;
          console.log('PDFPageViewer: Worker configured');
        }

        // Load the PDF document
        console.log('PDFPageViewer: Creating loading task for URL:', pdfUrl);
        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;
        console.log('PDFPageViewer: PDF loaded successfully, pages:', pdf.numPages);

        if (cancelled) return;

        // Check if page number is valid
        if (pageNumber < 1 || pageNumber > pdf.numPages) {
          throw new Error(`Invalid page number: ${pageNumber}`);
        }

        // Load the specific page
        const page = await pdf.getPage(pageNumber);
        
        if (cancelled) return;

        // Get page viewport
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        const highlightCanvas = highlightCanvasRef.current;
        
        if (!canvas || !highlightCanvas) return;

        // Set canvas dimensions
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        highlightCanvas.width = viewport.width;
        highlightCanvas.height = viewport.height;

        // Store page height for coordinate transformation
        const originalViewport = page.getViewport({ scale: 1 });
        setPageHeight(originalViewport.height);

        // Render PDF page to canvas
        const context = canvas.getContext('2d');
        if (!context) return;

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
          canvas: canvas, // Add canvas property required by RenderParameters
        };

        await page.render(renderContext).promise;

        if (!cancelled) {
          // Draw highlights after rendering
          drawHighlights(originalViewport.height, scale);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('PDFPageViewer: Error loading PDF:', {
            error: err,
            message: err instanceof Error ? err.message : 'Unknown error',
            pdfUrl,
            pageNumber
          });
          setError(err instanceof Error ? err.message : 'Failed to load PDF');
          setLoading(false);
        }
      }
    };

    loadPDF();

    return () => {
      cancelled = true;
    };
  }, [pdfUrl, pageNumber, scale, drawHighlights]);

  // Redraw highlights when scale changes
  useEffect(() => {
    if (pageHeight > 0) {
      drawHighlights(pageHeight, scale);
    }
  }, [scale, pageHeight, drawHighlights]);

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  };

  return (
    <div className={`relative bg-card rounded-lg ${className}`}>
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 z-10 flex gap-1 bg-background/80 backdrop-blur-sm rounded-md p-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleZoomOut}
          disabled={scale <= 0.5}
          className="h-8 w-8 p-0"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <span className="flex items-center px-2 text-xs text-muted-foreground">
          {Math.round(scale * 100)}%
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleZoomIn}
          disabled={scale >= 3}
          className="h-8 w-8 p-0"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
      </div>

      {/* Container for PDF and highlights */}
      <div 
        ref={containerRef}
        className="overflow-auto max-h-[600px] p-4"
        onClick={onPageClick}
      >
        <div className="relative inline-block">
          {/* PDF canvas */}
          <canvas
            ref={canvasRef}
            className="block border border-border shadow-sm"
          />
          
          {/* Highlight overlay canvas */}
          <canvas
            ref={highlightCanvasRef}
            className="absolute inset-0 pointer-events-none"
          />
          
          {/* Loading overlay */}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">Loading page {pageNumber}...</span>
              </div>
            </div>
          )}
          
          {/* Error overlay */}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm">
              <div className="flex flex-col items-center gap-2 p-4">
                <AlertCircle className="h-8 w-8 text-destructive" />
                <span className="text-sm text-destructive text-center">{error}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Page info */}
      {!loading && !error && (
        <div className="px-4 pb-2">
          <p className="text-xs text-muted-foreground">
            Page {pageNumber}
            {highlights.length > 0 && ` • ${highlights.length} highlight${highlights.length > 1 ? 's' : ''}`}
          </p>
        </div>
      )}
    </div>
  );
}