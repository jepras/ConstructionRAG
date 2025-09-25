'use client';

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import QueryInterface from './QueryInterface';
import SourcePanel from './SourcePanel';
import { SearchResult } from '@/lib/api-client';

interface ProjectQueryContentProps {
  projectSlug: string;
  runId: string;
  isAuthenticated: boolean;
  user?: any | null;
}

// Extract UUID from slug format for indexing run ID
function extractUUIDFromSlug(slug: string): string {
  const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const match = slug.match(uuidRegex);
  if (match) {
    return match[0];
  }
  // If no UUID found, return the original slug (might already be a UUID)
  return slug;
}

export default function ProjectQueryContent({
  projectSlug,
  runId,
  isAuthenticated,
  user
}: ProjectQueryContentProps) {
  const [selectedSource, setSelectedSource] = useState<SearchResult | undefined>(undefined);
  const [allSources, setAllSources] = useState<SearchResult[]>([]);
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q');

  // Extract the actual indexing run ID from the runId parameter
  const indexingRunId = extractUUIDFromSlug(runId);

  // Extract username and project slug from projectSlug (format: "username/project-name")
  const [username, actualProjectSlug] = projectSlug.split('/');
  const useUnifiedAPI = username && actualProjectSlug; // Use unified API if we have both parts

  // Debug logging
  console.log('🔍 ProjectQueryContent debug:', {
    projectSlug,
    username,
    actualProjectSlug,
    useUnifiedAPI,
    runId,
    indexingRunId
  });

  const handleNewQueryResponse = (searchResults: SearchResult[]) => {
    setAllSources(searchResults);
    // Automatically select the first (most relevant) source
    if (searchResults.length > 0) {
      setSelectedSource(searchResults[0]);
    }
  };

  const handleSourceChange = (source: SearchResult) => {
    setSelectedSource(source);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 lg:grid-rows-1 h-[calc(100vh-16rem)] lg:h-[calc(100vh-15rem)]">
      {/* Left Side - Query Interface */}
      <div className="min-w-0 flex flex-col col-span-1 lg:min-h-0">
        <div className="px-6 py-4 border-b border-border flex-shrink-0">
          <h1 className="text-2xl font-bold text-foreground">Project Q&A</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Ask questions about this project's documentation and get AI-powered answers.
          </p>
        </div>

        <div className="flex-1 min-h-0">
          <QueryInterface
            indexingRunId={indexingRunId}
            isAuthenticated={isAuthenticated}
            onQueryResponse={handleNewQueryResponse}
            onSourceSelect={handleSourceChange}
            selectedSource={selectedSource}
            initialQuery={initialQuery}
            useUnifiedAPI={useUnifiedAPI}
            username={username}
            projectSlug={actualProjectSlug}
          />
        </div>
      </div>

      {/* Right Side - Source Panel */}
      <div className="hidden lg:block col-span-1">
        <SourcePanel
          selectedSource={selectedSource}
          allSources={allSources}
          onSourceChange={handleSourceChange}
          indexingRunId={indexingRunId}
        />
      </div>
    </div>
  );
}