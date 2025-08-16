'use client';

import React from 'react';
import { FileText, Search, Download, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SourcePanelProps {
  selectedSource?: {
    filename: string;
    page?: number;
    content?: string;
  };
}

export default function SourcePanel({ selectedSource }: SourcePanelProps) {
  return (
    <div className="h-full flex flex-col bg-card border-l border-border">
      {/* Header */}
      <div className="bg-secondary p-3 flex items-center justify-between border-b border-border">
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-secondary-foreground">
            Source Documents
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <Button variant="ghost" size="sm" className="p-1">
            <Info className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" className="p-1">
            <Search className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" className="p-1">
            <Download className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-6">
        {selectedSource ? (
          <div className="text-center">
            <div className="mb-4">
              <FileText className="w-12 h-12 text-muted-foreground mx-auto" />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-2">
              {selectedSource.filename}
            </h3>
            {selectedSource.page && (
              <p className="text-xs text-muted-foreground mb-4">
                Page {selectedSource.page}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              PDF viewer integration coming soon
            </p>
          </div>
        ) : (
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
              Click on source citations in the chat to view the original documents here.
            </p>
            <div className="mt-6 p-4 bg-muted/30 rounded-lg">
              <p className="text-xs text-muted-foreground">
                <strong>Coming Soon:</strong> PDF rendering with highlighted citations and context navigation.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}