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
  selectedChunkId?: string;  // ID of the selected chunk to highlight differently
  scale?: number;
  onPageClick?: () => void;
  className?: string;
}

export default function PDFPageViewer({
  pdfUrl,
  pageNumber,
  highlights = [],
  selectedChunkId,
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

      // Draw each highlight
      highlights.forEach((highlight) => {
        if (!highlight || !highlight.bbox || highlight.bbox.length !== 4) return;
        
        // Use different styles for selected vs other highlights
        const isSelected = selectedChunkId && highlight.chunk_id === selectedChunkId;
        
        if (isSelected) {
          // Selected chunk: More prominent orange with higher opacity
          ctx.fillStyle = 'rgba(251, 146, 60, 0.5)'; // Orange with 50% opacity
        } else {
          // Other chunks: Lighter yellow with lower opacity
          ctx.fillStyle = 'rgba(250, 204, 21, 0.2)'; // Yellow with 20% opacity
        }
        
        const [x0, y0, x1, y1] = transformBboxToCanvas(highlight.bbox, pageHeight, scale);
        const width = x1 - x0;
        const height = y1 - y0;
        
        ctx.fillRect(x0, y0, width, height);
        
        // Add a border for the selected highlight
        if (isSelected) {
          ctx.strokeStyle = 'rgba(251, 146, 60, 0.8)'; // Orange border
          ctx.lineWidth = 2;
          ctx.strokeRect(x0, y0, width, height);
        }
      });
    },
    [highlights, selectedChunkId, transformBboxToCanvas]
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

        // Dynamically import PDF.js with proper error handling
        let pdfjsLib;
        try {
          pdfjsLib = await import('pdfjs-dist');
          console.log('PDFPageViewer: PDF.js loaded successfully');
        } catch (importError) {
          console.error('PDFPageViewer: Failed to import PDF.js:', importError);
          setError('Failed to load PDF viewer library');
          setLoading(false);
          return;
        }
        
        // Configure worker - use the correct path for the worker
        try {
          if (!pdfjsLib.GlobalWorkerOptions) {
            console.error('PDFPageViewer: GlobalWorkerOptions not found in pdfjsLib');
            // Try alternative import method
            const pdfjs = pdfjsLib.default || pdfjsLib;
            if (pdfjs.GlobalWorkerOptions) {
              pdfjs.GlobalWorkerOptions.workerSrc = `//cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjs.version || '4.0.379'}/build/pdf.worker.min.js`;
              console.log('PDFPageViewer: Worker configured using default export');
              pdfjsLib = pdfjs;
            } else {
              console.error('PDFPageViewer: Could not find GlobalWorkerOptions');
              setError('PDF viewer configuration error');
              setLoading(false);
              return;
            }
          } else {
            pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version || '4.0.379'}/build/pdf.worker.min.js`;
            console.log('PDFPageViewer: Worker configured');
          }
        } catch (workerError) {
          console.error('PDFPageViewer: Failed to configure worker:', workerError);
          setError('Failed to configure PDF viewer');
          setLoading(false);
          return;
        }

        // Load the PDF document
        console.log('PDFPageViewer: Creating loading task for URL:', pdfUrl);
        
        // Create loading task with error handling
        let loadingTask;
        try {
          loadingTask = pdfjsLib.getDocument({
            url: pdfUrl,
            withCredentials: false, // Don't send cookies with cross-origin request
            disableAutoFetch: false,
            disableStream: false,
          });
        } catch (taskError) {
          console.error('PDFPageViewer: Failed to create loading task:', taskError);
          setError('Failed to start PDF loading');
          setLoading(false);
          return;
        }
        
        // Add error handler for loading task
        loadingTask.onProgress = (progress: any) => {
          console.log('PDFPageViewer: Loading progress:', {
            loaded: progress.loaded,
            total: progress.total
          });
        };
        
        let pdf;
        try {
          pdf = await loadingTask.promise;
          console.log('PDFPageViewer: PDF loaded successfully, pages:', pdf.numPages);
        } catch (pdfError: any) {
          console.error('PDFPageViewer: Failed to load PDF document:', {
            error: pdfError,
            message: pdfError?.message,
            name: pdfError?.name,
            url: pdfUrl
          });
          setError(`Failed to load PDF: ${pdfError?.message || 'Unknown error'}`);
          setLoading(false);
          return;
        }

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

  // Redraw highlights when scale or selection changes
  useEffect(() => {
    if (pageHeight > 0) {
      drawHighlights(pageHeight, scale);
    }
  }, [scale, pageHeight, drawHighlights, selectedChunkId]);

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