'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { apiClient, QueryResponse, CreateQueryRequest } from '@/lib/api-client';
import QueryMessage from './QueryMessage';
import QueryInput from './QueryInput';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  searchResults?: QueryResponse['search_results'];
  isLoading?: boolean;
}

interface QueryInterfaceProps {
  indexingRunId: string;
  isAuthenticated?: boolean;
  onQueryResponse?: (searchResults: QueryResponse['search_results']) => void;
  onSourceSelect?: (source: QueryResponse['search_results'][0]) => void;
  selectedSource?: QueryResponse['search_results'][0];
  initialQuery?: string | null;
}

export default function QueryInterface({ 
  indexingRunId, 
  isAuthenticated,
  onQueryResponse,
  onSourceSelect,
  selectedSource,
  initialQuery
}: QueryInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [hasProcessedInitialQuery, setHasProcessedInitialQuery] = useState(false);
  const initialQueryProcessedRef = useRef(false);
  
  // Mount log
  useEffect(() => {
    console.log('🎪 QueryInterface MOUNTED with props:', {
      indexingRunId,
      isAuthenticated,
      initialQuery,
      hasOnQueryResponse: !!onQueryResponse,
      hasOnSourceSelect: !!onSourceSelect,
      selectedSource: !!selectedSource
    });
  }, []); // Only on mount

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const queryMutation = useMutation({
    mutationFn: (request: CreateQueryRequest) => {
      console.log('🔥 API REQUEST STARTED:', request);
      return apiClient.createQuery(request);
    },
    onSuccess: (response) => {
      console.log('✅ API SUCCESS:', {
        responseLength: response.response?.length,
        searchResultsCount: response.search_results?.length
      });
      
      // Update the assistant message with the actual response
      setMessages(prev => {
        console.log('🔄 Updating assistant message with response');
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage && lastMessage.type === 'assistant') {
          lastMessage.content = response.response;
          lastMessage.searchResults = response.search_results;
          lastMessage.isLoading = false;
        }
        return newMessages;
      });
      setIsTyping(false);
      
      // Notify parent component of new search results
      if (onQueryResponse && response.search_results) {
        console.log('QueryInterface: Search results received:', {
          count: response.search_results.length,
          firstResult: response.search_results[0] ? {
            hasDocumentId: !!response.search_results[0].document_id,
            hasMetadataDcoumentId: !!response.search_results[0].metadata?.document_id,
            hasBbox: !!response.search_results[0].bbox,
            hasMetadataBbox: !!response.search_results[0].metadata?.bbox,
            bbox: response.search_results[0].bbox || response.search_results[0].metadata?.bbox || 'none',
            metadata: response.search_results[0].metadata,
            chunk_id: response.search_results[0].chunk_id
          } : null
        });
        
        // Log all results to check bbox presence
        response.search_results.forEach((result, index) => {
          console.log(`QueryInterface: Result ${index} bbox:`, {
            hasBbox: !!result.bbox,
            hasMetadataBbox: !!result.metadata?.bbox,
            bbox: result.bbox || result.metadata?.bbox || 'none'
          });
        });
        
        onQueryResponse(response.search_results);
      }
    },
    onError: (error: any) => {
      console.log('❌ API ERROR:', error);
      
      // Update the assistant message with error
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage && lastMessage.type === 'assistant') {
          lastMessage.content = 'Sorry, I encountered an error while processing your query. Please try again.';
          lastMessage.isLoading = false;
        }
        return newMessages;
      });
      setIsTyping(false);
      toast.error(error.message || 'Failed to get response');
    }
  });

  const handleSubmit = useCallback(async (query: string) => {
    console.log('🎯 handleSubmit called with query:', query);
    console.log('📊 Current messages count:', messages.length);
    
    if (!query.trim()) {
      console.log('❌ handleSubmit: Empty query, returning');
      return;
    }

    console.log('🚀 handleSubmit: Submitting query to API');

    // Add user message and loading assistant message in single setState
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: query,
      timestamp: new Date(),
    };
    const assistantMessage: Message = {
      id: `assistant-${Date.now() + 1}`, // Ensure unique ID
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };
    setMessages(prev => {
      console.log('📝 handleSubmit: Adding both user and loading messages');
      return [...prev, userMessage, assistantMessage];
    });
    setIsTyping(true);

    // Make the API call
    console.log('🌐 handleSubmit: Making API call with query:', query);
    queryMutation.mutate({
      query,
      indexing_run_id: indexingRunId,
    });
  }, [queryMutation, indexingRunId, messages.length]);

  // Handle initial query from URL parameter
  useEffect(() => {
    console.log('🔍 QueryInterface useEffect triggered:', {
      initialQuery,
      hasProcessedInitialQuery,
      initialQueryProcessedRef: initialQueryProcessedRef.current,
      mutationStatus: queryMutation.status,
      messagesCount: messages.length
    });
    
    if (initialQuery && !initialQueryProcessedRef.current) {
      console.log('✅ Processing initial query:', initialQuery);
      initialQueryProcessedRef.current = true;
      setHasProcessedInitialQuery(true);
      
      if (!initialQuery.trim()) {
        console.log('❌ Empty query, returning');
        return;
      }

      console.log('🚀 Submitting initial query to API');
      
      // Use a single setState call to add both messages at once
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        type: 'user',
        content: initialQuery,
        timestamp: new Date(),
      };

      const assistantMessage: Message = {
        id: `assistant-${Date.now() + 1}`, // Ensure unique ID
        type: 'assistant',
        content: '',
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages(prev => {
        console.log('📝 Adding both user and loading messages');
        return [...prev, userMessage, assistantMessage];
      });
      setIsTyping(true);

      // Make the API call
      console.log('🌐 Making API call with query:', initialQuery);
      queryMutation.mutate({
        query: initialQuery,
        indexing_run_id: indexingRunId,
      });
    } else {
      console.log('⏭️ Skipping initial query processing:', {
        hasInitialQuery: !!initialQuery,
        alreadyProcessedRef: initialQueryProcessedRef.current,
        alreadyProcessedState: hasProcessedInitialQuery
      });
    }
  }, [initialQuery]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="mx-auto w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Start a Conversation</h3>
            <p className="text-muted-foreground text-sm max-w-md mx-auto">
              Ask questions about the project documentation and get AI-powered answers with source citations.
            </p>
            <div className="mt-6 space-y-2">
              <p className="text-xs text-muted-foreground">Example questions:</p>
              <div className="flex flex-wrap gap-2 justify-center">
                <button
                  onClick={() => handleSubmit("What are the project requirements?")}
                  className="px-3 py-1 text-xs bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded-full transition-colors"
                >
                  What are the project requirements?
                </button>
                <button
                  onClick={() => handleSubmit("What is the timeline for completion?")}
                  className="px-3 py-1 text-xs bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded-full transition-colors"
                >
                  What is the timeline?
                </button>
                <button
                  onClick={() => handleSubmit("What materials are specified?")}
                  className="px-3 py-1 text-xs bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded-full transition-colors"
                >
                  What materials are specified?
                </button>
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <QueryMessage
              key={message.id}
              message={message}
              isTyping={isTyping && message.isLoading}
              onSourceSelect={onSourceSelect}
              selectedSourceId={selectedSource?.chunk_id}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border px-6 py-4">
        <QueryInput
          onSubmit={handleSubmit}
          disabled={queryMutation.isPending}
          placeholder="Ask anything about the project..."
        />
      </div>
    </div>
  );
}