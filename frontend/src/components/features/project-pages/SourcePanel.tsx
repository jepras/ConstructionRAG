'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { FileText, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SearchResult } from '@/lib/api-client';
import { PDFPageViewer, PDFFullViewer } from './PDFViewerWrapper';
import { deduplicateBboxHighlights } from '@/lib/utils';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';

interface SourcePanelProps {
  selectedSource?: SearchResult;
  allSources?: SearchResult[];
  onSourceChange?: (source: SearchResult) => void;
  indexingRunId?: string;
}

export default function SourcePanel({ 
  selectedSource, 
  allSources = [],
  onSourceChange,
  indexingRunId
}: SourcePanelProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [showFullViewer, setShowFullViewer] = useState(false);
  const [pdfViewerKey, setPdfViewerKey] = useState(0);
  
  // Cache PDF URLs to avoid refetching
  const [pdfUrlCache, setPdfUrlCache] = useState<Map<string, string>>(new Map());
  
  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const loadingAbortControllerRef = useRef<AbortController | null>(null);

  // Load PDF URL when source changes with debouncing
  useEffect(() => {
    // Clear any existing debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    // Abort any in-flight PDF loading
    if (loadingAbortControllerRef.current) {
      loadingAbortControllerRef.current.abort();
    }

    const currentDocId = selectedSource?.metadata?.document_id || selectedSource?.document_id;
    const previousDocId = pdfUrl ? 'has-url' : 'no-url';
    

    if (selectedSource?.metadata?.document_id || selectedSource?.document_id) {
      // Debounce the PDF loading by 300ms
      debounceTimerRef.current = setTimeout(() => {
        const loadPdfUrl = async () => {
        const documentId = selectedSource.metadata?.document_id || selectedSource.document_id;
        if (!documentId) {
          setPdfError('No document ID found');
          return;
        }

        // Create cache key
        const cacheKey = `${documentId}-${indexingRunId || 'auth'}`;
        
        // Check cache first
        if (pdfUrlCache.has(cacheKey)) {
          const cachedUrl = pdfUrlCache.get(cacheKey)!;
          setPdfUrl(cachedUrl);
          // Force re-render of PDF viewer with new key
          setPdfViewerKey(prev => prev + 1);
          return;
        }

        // Create new abort controller for this request
        const abortController = new AbortController();
        loadingAbortControllerRef.current = abortController;

        const apiStartTime = performance.now();
        setLoadingPdf(true);
        setPdfError(null);
        
        try {

          // Build URL with optional indexingRunId for anonymous access
          const params = new URLSearchParams();
          if (indexingRunId) {
            params.append('index_run_id', indexingRunId);
          }
          
          const url = `/api/documents/${documentId}/pdf${params.toString() ? '?' + params.toString() : ''}`;
          
          const response = await fetch(url, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            signal: abortController.signal,
          });


          if (!response.ok) {
            const errorText = await response.text();
            console.error('SourcePanel: PDF endpoint error response:', errorText);
            throw new Error(`Failed to get PDF URL: ${response.status} ${response.statusText}`);
          }

          const data = await response.json();
          
          if (!data.url) {
            throw new Error('No PDF URL in response');
          }
          
          // Cache the URL
          setPdfUrlCache(prev => new Map(prev.set(cacheKey, data.url)));
          setPdfUrl(data.url);
          // Force re-render of PDF viewer with new key
          setPdfViewerKey(prev => prev + 1);
        } catch (error: any) {
          // Ignore abort errors
          if (error?.name === 'AbortError') {
            console.log('SourcePanel: PDF loading was aborted');
            return;
          }
          console.error('SourcePanel: Error loading PDF:', error);
          setPdfError(error instanceof Error ? error.message : 'Failed to load PDF');
        } finally {
          setLoadingPdf(false);
          loadingAbortControllerRef.current = null;
        }
      };

      loadPdfUrl();
      }, 300); // 300ms debounce delay
    } else {
      console.log('SourcePanel: No source selected or no document ID');
      setPdfUrl(null);
      setPdfViewerKey(prev => prev + 1);
    }
    
    // Cleanup function
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (loadingAbortControllerRef.current) {
        loadingAbortControllerRef.current.abort();
      }
    };
  }, [selectedSource, indexingRunId]);

  // Prepare highlights for all sources on the same page and document as the selected source
  const currentHighlights = selectedSource && allSources
    ? (() => {
        const rawHighlights = allSources
          .filter(source => 
            // Only include sources from the same page and document
            (source?.page_number || source?.metadata?.page_number) === 
              (selectedSource?.page_number || selectedSource?.metadata?.page_number) &&
            (source?.document_id || source?.metadata?.document_id) === 
              (selectedSource?.document_id || selectedSource?.metadata?.document_id)
          )
          .map(source => ({
            bbox: source?.bbox || source?.metadata?.bbox,
            chunk_id: source?.chunk_id,
          }))
          .filter((h) => {
            return h?.bbox !== undefined && Array.isArray(h.bbox) && h.bbox.length === 4;
          }) as Array<{ bbox: number[]; chunk_id?: string }>;
        
        // Apply deduplication to remove overlapping/identical bboxes
        return deduplicateBboxHighlights(rawHighlights, 0.8, 1);
      })()
    : [];
  
  // Debug logging for bbox deduplication
  console.log('SourcePanel: highlights check:', {
    selectedSourcePage: selectedSource?.page_number || selectedSource?.metadata?.page_number,
    selectedSourceDoc: selectedSource?.document_id || selectedSource?.metadata?.document_id,
    totalSources: allSources?.length || 0,
    rawHighlightsCount: selectedSource && allSources ? allSources
      .filter(source => 
        (source?.page_number || source?.metadata?.page_number) === 
          (selectedSource?.page_number || selectedSource?.metadata?.page_number) &&
        (source?.document_id || source?.metadata?.document_id) === 
          (selectedSource?.document_id || selectedSource?.metadata?.document_id)
      )
      .filter(source => (source?.bbox || source?.metadata?.bbox)?.length === 4).length : 0,
    deduplicatedHighlightsCount: currentHighlights.length,
    currentHighlights: currentHighlights,
  });

  // Get all highlights for full viewer (from all sources for the same document)
  const allHighlights = allSources && selectedSource
    ? (() => {
        // Group highlights by page for per-page deduplication
        const highlightsByPage = new Map<number, Array<{ bbox: number[], chunk_id?: string }>>();
        
        allSources
          .filter(s => 
            (s?.metadata?.document_id || s?.document_id) === 
            (selectedSource?.metadata?.document_id || selectedSource?.document_id)
          )
          .forEach(s => {
            const pageNumber = s?.page_number || s?.metadata?.page_number || 1;
            const bbox = s?.bbox || s?.metadata?.bbox;
            
            if (bbox && bbox.length === 4) {
              if (!highlightsByPage.has(pageNumber)) {
                highlightsByPage.set(pageNumber, []);
              }
              highlightsByPage.get(pageNumber)!.push({
                bbox,
                chunk_id: s?.chunk_id
              });
            }
          });
        
        // Deduplicate highlights on each page and convert back to full format
        const deduplicatedHighlights: Array<{
          page_number: number,
          bbox: number[],
          chunk_id?: string
        }> = [];
        
        Array.from(highlightsByPage.entries()).forEach(([pageNumber, pageHighlights]) => {
          const deduplicated = deduplicateBboxHighlights(pageHighlights, 0.8, 1);
          deduplicated.forEach(h => {
            deduplicatedHighlights.push({
              page_number: pageNumber,
              bbox: h.bbox,
              chunk_id: h.chunk_id
            });
          });
        });
        
        return deduplicatedHighlights;
      })()
    : [];

  return (
    <>
      <div className="h-full flex flex-col bg-card border-l border-border">
        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {selectedSource ? (
            <div className="h-full flex flex-col">
              {/* Source info */}
              <div className="px-4 py-3 border-b border-border bg-background">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground truncate">
                    {selectedSource.source_filename}
                  </h3>
                </div>
                <div className="flex items-center gap-3 mt-1">
                  {(selectedSource.page_number || selectedSource.metadata?.page_number) && (
                    <span className="text-xs text-muted-foreground">
                      Page {selectedSource.page_number || selectedSource.metadata?.page_number}
                    </span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {Math.round(selectedSource.similarity_score * 100)}% match
                  </span>
                  {currentHighlights.length > 1 && (
                    <span className="text-xs text-muted-foreground">
                      • {currentHighlights.length} sources on this page
                    </span>
                  )}
                </div>
              </div>

              {/* PDF Preview */}
              <div className="flex-1 overflow-hidden">
                {loadingPdf ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      <span className="text-sm text-muted-foreground">Loading PDF...</span>
                    </div>
                  </div>
                ) : pdfError ? (
                  <div className="h-full flex items-center justify-center p-6">
                    <div className="text-center">
                      <div className="mb-4">
                        <FileText className="w-12 h-12 text-muted-foreground mx-auto" />
                      </div>
                      <p className="text-sm text-destructive mb-2">Failed to load PDF</p>
                      <p className="text-xs text-muted-foreground">{pdfError}</p>
                    </div>
                  </div>
                ) : pdfUrl ? (
                  <ErrorBoundary
                    fallback={({ error, retry }) => (
                      <div className="h-full flex items-center justify-center p-6">
                        <div className="text-center">
                          <div className="mb-4">
                            <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
                          </div>
                          <p className="text-sm text-destructive mb-2">PDF viewer error</p>
                          <p className="text-xs text-muted-foreground mb-4">
                            {error?.message || 'The PDF viewer encountered an error'}
                          </p>
                          <Button 
                            onClick={() => {
                              setPdfViewerKey(prev => prev + 1);
                              retry?.();
                            }}
                            size="sm"
                            variant="outline"
                            className="gap-2"
                          >
                            <RefreshCw className="h-3 w-3" />
                            Retry
                          </Button>
                        </div>
                      </div>
                    )}
                    key={pdfViewerKey}
                  >
                    <PDFPageViewer
                      key={`${pdfUrl}-${pdfViewerKey}`}
                      pdfUrl={pdfUrl}
                      pageNumber={selectedSource.page_number || selectedSource.metadata?.page_number || 1}
                      highlights={currentHighlights}
                      selectedChunkId={selectedSource.chunk_id}
                      scale={1.2}
                      className="h-full"
                    />
                  </ErrorBoundary>
                ) : (
                  <div className="h-full flex items-center justify-center p-6">
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground">
                        No PDF available for this source
                      </p>
                    </div>
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-6">
              <div className="text-center">
                <div className="mb-4">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                    <FileText className="w-8 h-8 text-muted-foreground" />
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-2">
                  Source Viewer
                </h3>
                <p className="text-xs text-muted-foreground max-w-xs">
                  Ask a question to see source documents with highlighted relevant sections.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Full PDF Viewer Modal */}
      {selectedSource && pdfUrl && (
        <PDFFullViewer
          isOpen={showFullViewer}
          onClose={() => setShowFullViewer(false)}
          pdfUrl={pdfUrl}
          filename={selectedSource.source_filename}
          initialPage={selectedSource.page_number || selectedSource.metadata?.page_number || 1}
          highlights={allHighlights}
          selectedChunkId={selectedSource.chunk_id}
        />
      )}
    </>
  );
}