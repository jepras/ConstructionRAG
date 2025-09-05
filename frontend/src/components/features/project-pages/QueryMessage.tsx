'use client';

import React, { useState } from 'react';
import { MessageSquare, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { QueryResponse } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import SourceViewerModal from './SourceViewerModal';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface QueryMessageProps {
  message: {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    searchResults?: QueryResponse['search_results'];
    isLoading?: boolean;
  };
  isTyping?: boolean;
  onSourceSelect?: (source: QueryResponse['search_results'][0]) => void;
  selectedSourceId?: string;
}

export default function QueryMessage({ message, isTyping, onSourceSelect, selectedSourceId }: QueryMessageProps) {
  const isUser = message.type === 'user';
  const [selectedSource, setSelectedSource] = useState<QueryResponse['search_results'][0] | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSourcesExpanded, setIsSourcesExpanded] = useState(false); // Collapsed by default

  const handleSourceClick = (source: QueryResponse['search_results'][0]) => {
    // If onSourceSelect is provided, use it for the source panel
    if (onSourceSelect) {
      onSourceSelect(source);
    } else {
      // Otherwise show the modal (fallback behavior)
      setSelectedSource(source);
      setIsModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedSource(null);
  };

  const renderSourceButton = (result: QueryResponse['search_results'][0], index: number) => {
    const isSelected = selectedSourceId === result.chunk_id;
    
    return (
      <button
        key={index}
        className={cn(
          "block w-full text-left px-2 py-1 rounded transition-colors group cursor-pointer border",
          isSelected
            ? "bg-primary/10 border-primary hover:bg-primary/20"
            : "hover:bg-muted/50 border-transparent hover:border-border"
        )}
        onClick={() => handleSourceClick(result)}
        title={onSourceSelect ? "Click to view in source panel" : "Click to view full source text"}
      >
        <div className="flex items-center justify-between">
          <span className={cn(
            "text-xs flex items-center gap-1",
            isSelected
              ? "text-primary font-medium"
              : "text-muted-foreground group-hover:text-foreground"
          )}>
            <FileText className="w-3 h-3" />
            {result.source_filename}
            {result.page_number && ` • Page ${result.page_number}`}
          </span>
          <span className={cn(
            "text-xs",
            isSelected ? "text-primary" : "text-muted-foreground"
          )}>
            {Math.round(result.similarity_score * 100)}% match
          </span>
        </div>
      </button>
    );
  };

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="bg-primary text-primary-foreground px-4 py-2 rounded-lg max-w-md">
          <p className="text-sm">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start space-x-3">
      <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
        <MessageSquare className="w-4 h-4 text-primary-foreground" />
      </div>
      <div className="flex-1 max-w-2xl">
        <div className="bg-secondary rounded-lg px-4 py-3">
          {isTyping ? (
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
              <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
            </div>
          ) : (
            <>
              <p className="text-sm text-secondary-foreground whitespace-pre-wrap">
                {message.content}
              </p>
              
              {/* Source Citations */}
              {message.searchResults && message.searchResults.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground">
                      Sources ({message.searchResults.length})
                    </span>
                  </div>
                  
                  <Collapsible open={isSourcesExpanded} onOpenChange={setIsSourcesExpanded}>
                    <CollapsibleTrigger asChild>
                      <button className="flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-2">
                        {isSourcesExpanded ? (
                          <>
                            <ChevronUp className="w-3 h-3" />
                            Hide sources
                          </>
                        ) : (
                          <>
                            <ChevronDown className="w-3 h-3" />
                            Show sources
                          </>
                        )}
                      </button>
                    </CollapsibleTrigger>
                    
                    <CollapsibleContent className="space-y-1">
                      {message.searchResults.map((result, index) => 
                        renderSourceButton(result, index)
                      )}
                    </CollapsibleContent>
                  </Collapsible>
                </div>
              )}
            </>
          )}
        </div>
        
        {/* Timestamp */}
        {!isTyping && (
          <div className="mt-1 px-1">
            <span className="text-xs text-muted-foreground">
              {new Date(message.timestamp).toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
              })}
            </span>
          </div>
        )}
      </div>
      
      <SourceViewerModal 
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        searchResult={selectedSource}
      />
    </div>
  );
}