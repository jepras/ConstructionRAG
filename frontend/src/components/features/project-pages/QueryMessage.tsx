'use client';

import React from 'react';
import { MessageSquare, FileText } from 'lucide-react';
import { QueryResponse } from '@/lib/api-client';
import { cn } from '@/lib/utils';

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
}

export default function QueryMessage({ message, isTyping }: QueryMessageProps) {
  const isUser = message.type === 'user';

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
                    <span className="text-xs font-medium text-muted-foreground">Sources</span>
                  </div>
                  <div className="space-y-1">
                    {message.searchResults.slice(0, 3).map((result, index) => (
                      <button
                        key={index}
                        className="block w-full text-left px-2 py-1 rounded hover:bg-muted/50 transition-colors group"
                        onClick={() => {
                          // TODO: Implement source viewer
                          console.log('View source:', result);
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-muted-foreground group-hover:text-foreground">
                            {result.source_filename}
                            {result.page_number && ` • Page ${result.page_number}`}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {Math.round(result.similarity_score * 100)}% match
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
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
    </div>
  );
}