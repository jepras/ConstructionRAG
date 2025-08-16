'use client';

import React, { useState } from 'react';
import QueryInterface from './QueryInterface';
import SourcePanel from './SourcePanel';

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
  const [selectedSource, setSelectedSource] = useState<any>(null);
  
  // Extract the actual indexing run ID from the runId parameter
  const indexingRunId = extractUUIDFromSlug(runId);

  return (
    <div className="h-full flex">
      {/* Left Side - Query Interface */}
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="px-6 py-4 border-b border-border">
          <h1 className="text-2xl font-bold text-foreground">Project Q&A</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Ask questions about this project's documentation and get AI-powered answers.
          </p>
        </div>
        
        <div className="flex-1 overflow-hidden">
          <QueryInterface 
            indexingRunId={indexingRunId}
            isAuthenticated={isAuthenticated}
          />
        </div>
      </div>

      {/* Right Side - Source Panel */}
      <div className="hidden lg:block w-96">
        <SourcePanel selectedSource={selectedSource} />
      </div>
    </div>
  );
}