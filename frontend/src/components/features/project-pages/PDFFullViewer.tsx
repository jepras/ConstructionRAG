'use client';

import React, { useState } from 'react';
import { X, ChevronLeft, ChevronRight, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import PDFPageViewer from './PDFPageViewer';

interface PDFFullViewerProps {
  isOpen: boolean;
  onClose: () => void;
  pdfUrl: string;
  filename: string;
  initialPage?: number;
  totalPages?: number;
  highlights?: Array<{
    page_number: number;
    bbox: number[];
    chunk_id?: string;
  }>;
}

export default function PDFFullViewer({
  isOpen,
  onClose,
  pdfUrl,
  filename,
  initialPage = 1,
  totalPages,
  highlights = [],
}: PDFFullViewerProps) {
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageCount, setPageCount] = useState(totalPages || 1);
  const [loadingPageCount, setLoadingPageCount] = useState(!totalPages);

  // Get highlights for current page
  const currentPageHighlights = highlights
    ? highlights
        .filter(h => h && h.page_number === currentPage)
        .map(h => ({ bbox: h.bbox, chunk_id: h.chunk_id }))
    : [];

  // Load total page count if not provided
  React.useEffect(() => {
    if (!totalPages && isOpen && typeof window !== 'undefined') {
      const loadPageCount = async () => {
        try {
          setLoadingPageCount(true);
          const pdfjsLib = await import('pdfjs-dist');
          
          // Configure worker
          if (pdfjsLib.GlobalWorkerOptions) {
            pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.js`;
          }
          
          const loadingTask = pdfjsLib.getDocument(pdfUrl);
          const pdf = await loadingTask.promise;
          setPageCount(pdf.numPages);
        } catch (error) {
          console.error('Error loading PDF page count:', error);
        } finally {
          setLoadingPageCount(false);
        }
      };
      
      loadPageCount();
    }
  }, [pdfUrl, totalPages, isOpen]);

  // Reset to initial page when modal opens
  React.useEffect(() => {
    if (isOpen) {
      setCurrentPage(initialPage);
    }
  }, [isOpen, initialPage]);

  const handlePreviousPage = () => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  };

  const handleNextPage = () => {
    setCurrentPage(prev => Math.min(pageCount, prev + 1));
  };

  const handlePageInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const page = parseInt(e.target.value, 10);
    if (!isNaN(page) && page >= 1 && page <= pageCount) {
      setCurrentPage(page);
    }
  };

  // Get pages with highlights for quick navigation
  const pagesWithHighlights = highlights && highlights.length > 0
    ? [...new Set(highlights.filter(h => h && h.page_number).map(h => h.page_number))].sort((a, b) => a - b)
    : [];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] flex flex-col p-0">
        {/* Header */}
        <DialogHeader className="px-6 py-4 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <DialogTitle className="text-lg font-semibold">
                {filename}
              </DialogTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        {/* PDF Viewer */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <PDFPageViewer
            pdfUrl={pdfUrl}
            pageNumber={currentPage}
            highlights={currentPageHighlights}
            scale={1.2}
            className="h-full"
          />
        </div>

        {/* Footer with navigation */}
        <div className="px-6 py-3 border-t border-border bg-secondary/30">
          <div className="flex items-center justify-between">
            {/* Page navigation */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePreviousPage}
                disabled={currentPage <= 1}
                className="h-8"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={currentPage}
                  onChange={handlePageInput}
                  className="w-12 px-2 py-1 text-sm text-center border border-border rounded bg-background"
                  min={1}
                  max={pageCount}
                />
                <span className="text-sm text-muted-foreground">
                  of {loadingPageCount ? '...' : pageCount}
                </span>
              </div>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleNextPage}
                disabled={currentPage >= pageCount}
                className="h-8"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Quick jump to highlighted pages */}
            {pagesWithHighlights.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  Highlighted pages:
                </span>
                <div className="flex gap-1">
                  {pagesWithHighlights.slice(0, 5).map(page => (
                    <Button
                      key={page}
                      variant={currentPage === page ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCurrentPage(page)}
                      className="h-7 px-2 text-xs"
                    >
                      {page}
                    </Button>
                  ))}
                  {pagesWithHighlights.length > 5 && (
                    <span className="text-xs text-muted-foreground px-2">
                      +{pagesWithHighlights.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Highlight count */}
            {currentPageHighlights.length > 0 && (
              <div className="text-xs text-muted-foreground">
                {currentPageHighlights.length} highlight{currentPageHighlights.length > 1 ? 's' : ''} on this page
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}