'use client';

import React from 'react';
import { FileText, X } from 'lucide-react';
import { QueryResponse } from '@/lib/api-client';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface SourceViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  searchResult: QueryResponse['search_results'][0] | null;
}

export default function SourceViewerModal({ isOpen, onClose, searchResult }: SourceViewerModalProps) {
  if (!searchResult) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col sm:max-w-3xl md:max-w-4xl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="w-5 h-5 text-primary" />
              <DialogTitle className="text-lg font-semibold text-foreground">
                Source Document
              </DialogTitle>
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onClose}
              className="h-8 w-8 p-0"
              aria-label="Close source viewer"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          <DialogDescription className="text-left">
            <div className="space-y-1 text-sm text-muted-foreground">
              <div className="flex items-center space-x-4">
                <span><strong>File:</strong> {searchResult.source_filename}</span>
                {searchResult.page_number && (
                  <span><strong>Page:</strong> {searchResult.page_number}</span>
                )}
                <span><strong>Match:</strong> {Math.round(searchResult.similarity_score * 100)}%</span>
              </div>
            </div>
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto">
            <div className="bg-secondary rounded-lg p-4 border border-border">
              <div className="text-sm text-card-foreground whitespace-pre-wrap leading-relaxed font-mono">
                {searchResult.content}
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex justify-end pt-4 border-t border-border">
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}