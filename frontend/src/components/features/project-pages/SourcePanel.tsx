'use client';

import React, { useState, useEffect } from 'react';
import { FileText, Maximize2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SearchResult } from '@/lib/api-client';
import { PDFPageViewer, PDFFullViewer } from './PDFViewerWrapper';

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

  // Load PDF URL when source changes
  useEffect(() => {
    console.log('SourcePanel: Source changed', {
      selectedSource,
      hasDocumentId: !!(selectedSource?.metadata?.document_id || selectedSource?.document_id),
      documentId: selectedSource?.metadata?.document_id || selectedSource?.document_id,
      indexingRunId
    });

    if (selectedSource?.metadata?.document_id || selectedSource?.document_id) {
      const loadPdfUrl = async () => {
        setLoadingPdf(true);
        setPdfError(null);
        
        try {
          const documentId = selectedSource.metadata?.document_id || selectedSource.document_id;
          console.log('SourcePanel: Loading PDF for document:', documentId);
          
          if (!documentId) {
            throw new Error('No document ID found');
          }

          // Build URL with optional indexingRunId for anonymous access
          const params = new URLSearchParams();
          if (indexingRunId) {
            params.append('index_run_id', indexingRunId);
          }
          
          const url = `/api/documents/${documentId}/pdf${params.toString() ? '?' + params.toString() : ''}`;
          console.log('SourcePanel: Fetching PDF from URL:', url);
          
          const response = await fetch(url, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          });

          console.log('SourcePanel: PDF endpoint response:', {
            ok: response.ok,
            status: response.status,
            statusText: response.statusText
          });

          if (!response.ok) {
            const errorText = await response.text();
            console.error('SourcePanel: PDF endpoint error response:', errorText);
            throw new Error(`Failed to get PDF URL: ${response.status} ${response.statusText}`);
          }

          const data = await response.json();
          console.log('SourcePanel: PDF URL received:', {
            hasUrl: !!data.url,
            url: data.url, // Log the actual URL for debugging
            filename: data.filename,
            expiresIn: data.expires_in,
            fullResponse: data
          });
          
          if (!data.url) {
            console.error('SourcePanel: No URL in response data:', data);
            throw new Error('No PDF URL in response');
          }
          
          setPdfUrl(data.url);
        } catch (error) {
          console.error('SourcePanel: Error loading PDF:', error);
          setPdfError(error instanceof Error ? error.message : 'Failed to load PDF');
        } finally {
          setLoadingPdf(false);
        }
      };

      loadPdfUrl();
    } else {
      console.log('SourcePanel: No source selected or no document ID');
      setPdfUrl(null);
    }
  }, [selectedSource, indexingRunId]);

  // Prepare highlights for all sources on the same page and document as the selected source
  const currentHighlights = selectedSource && allSources
    ? allSources
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
        .filter(h => h?.bbox && h.bbox.length === 4)
    : [];
  
  // Debug logging for bbox
  console.log('SourcePanel: highlights check:', {
    selectedSourcePage: selectedSource?.page_number || selectedSource?.metadata?.page_number,
    selectedSourceDoc: selectedSource?.document_id || selectedSource?.metadata?.document_id,
    totalSources: allSources?.length || 0,
    highlightsOnPage: currentHighlights.length,
    currentHighlights: currentHighlights,
  });

  // Get all highlights for full viewer (from all sources for the same document)
  const allHighlights = allSources && selectedSource
    ? allSources
        .filter(s => 
          (s?.metadata?.document_id || s?.document_id) === 
          (selectedSource?.metadata?.document_id || selectedSource?.document_id)
        )
        .map(s => ({
          page_number: s?.page_number || s?.metadata?.page_number || 1,
          bbox: s?.bbox || s?.metadata?.bbox || [],
          chunk_id: s?.chunk_id
        }))
        .filter(h => h?.bbox && h.bbox.length === 4)
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
                  {pdfUrl && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="p-1 ml-2"
                      onClick={() => setShowFullViewer(true)}
                      title="View full document"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </Button>
                  )}
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
                  <PDFPageViewer
                    pdfUrl={pdfUrl}
                    pageNumber={selectedSource.page_number || selectedSource.metadata?.page_number || 1}
                    highlights={currentHighlights}
                    selectedChunkId={selectedSource.chunk_id}
                    scale={1.2}
                    onPageClick={() => setShowFullViewer(true)}
                    className="h-full"
                  />
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