'use client';

import React from 'react';

interface ProjectIndexingContentProps {
  projectSlug: string;
  runId: string;
  isAuthenticated: boolean;
  user?: any | null;
}

interface ProcessingStep {
  step: string;
  status: 'completed' | 'processing' | 'pending' | 'failed';
  description: string;
}

const PROCESSING_STEPS: ProcessingStep[] = [
  { step: 'Document Partitioning', status: 'completed', description: 'Extract text, tables, and images from documents' },
  { step: 'Metadata Extraction', status: 'completed', description: 'Extract document structure and metadata' },
  { step: 'Content Enrichment', status: 'completed', description: 'Generate descriptions for tables and images' },
  { step: 'Semantic Chunking', status: 'completed', description: 'Break content into searchable chunks' },
  { step: 'Vector Embedding', status: 'completed', description: 'Generate embeddings for semantic search' },
  { step: 'Wiki Generation', status: 'completed', description: 'Create structured wiki documentation' },
];

function getStatusColor(status: ProcessingStep['status']) {
  switch (status) {
    case 'completed':
      return 'bg-green-500';
    case 'processing':
      return 'bg-yellow-500';
    case 'pending':
      return 'bg-gray-400';
    case 'failed':
      return 'bg-red-500';
    default:
      return 'bg-gray-400';
  }
}

function getStatusText(status: ProcessingStep['status']) {
  switch (status) {
    case 'completed':
      return 'Completed';
    case 'processing':
      return 'Processing';
    case 'pending':
      return 'Pending';
    case 'failed':
      return 'Failed';
    default:
      return 'Unknown';
  }
}

export default function ProjectIndexingContent({ 
  projectSlug, 
  runId, 
  isAuthenticated, 
  user 
}: ProjectIndexingContentProps) {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          {isAuthenticated ? "Indexing Progress" : "Indexing Information"}
        </h1>
        <p className="text-muted-foreground">
          {isAuthenticated 
            ? "View the progress and details of document processing for this project."
            : "View information about the document processing for this project."
          }
        </p>
      </div>

      <div className="space-y-6">
        {/* Current Run Status */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Current Indexing Run</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Run ID</span>
              <span className="text-sm text-muted-foreground font-mono">{runId}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Status</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm text-foreground">Completed</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Access Level</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isAuthenticated ? 'bg-green-500' : 'bg-blue-500'}`}></div>
                <span className="text-sm text-foreground">{isAuthenticated ? 'Private' : 'Public'}</span>
              </div>
            </div>
            {isAuthenticated && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-foreground">Project</span>
                <span className="text-sm text-muted-foreground font-mono">{projectSlug}</span>
              </div>
            )}
          </div>
        </div>

        {/* Processing Pipeline */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Processing Pipeline</h2>
          <div className="space-y-3">
            {PROCESSING_STEPS.map((step, index) => (
              <div key={index} className="flex items-center gap-3 p-3 bg-muted/50 rounded-md">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 ${getStatusColor(step.status)} rounded-full`}></div>
                  <span className="text-sm font-medium text-foreground">{step.step}</span>
                </div>
                <span className="text-xs text-muted-foreground">• {step.description}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Statistics */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Processing Statistics</h2>
          {isAuthenticated ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary mb-1">-</div>
                <div className="text-xs text-muted-foreground">Documents</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary mb-1">-</div>
                <div className="text-xs text-muted-foreground">Pages</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary mb-1">-</div>
                <div className="text-xs text-muted-foreground">Chunks</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-primary mb-1">-</div>
                <div className="text-xs text-muted-foreground">Embeddings</div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">
                Detailed processing statistics are available for project owners.
              </p>
              <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                <div className="text-center">
                  <div className="text-lg font-semibold text-foreground mb-1">✓</div>
                  <div className="text-xs text-muted-foreground">Processing Complete</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-foreground mb-1">📊</div>
                  <div className="text-xs text-muted-foreground">Data Available</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Context-specific additional info */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">
            {isAuthenticated ? "Advanced Features" : "Public Access"}
          </h2>
          {isAuthenticated ? (
            <div>
              <p className="text-muted-foreground mb-4">
                As the project owner, you have access to detailed indexing information and controls.
              </p>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Detailed processing logs and timing</li>
                <li>• Re-indexing and update controls</li>
                <li>• Advanced configuration options</li>
                <li>• Export and backup features</li>
              </ul>
              <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md dark:bg-blue-900/20 dark:border-blue-700/50">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  <strong>Coming Soon:</strong> Advanced indexing controls and detailed analytics will be available in future updates.
                </p>
              </div>
            </div>
          ) : (
            <div>
              <p className="text-muted-foreground mb-3">
                This project has been processed and made publicly available. The indexing pipeline successfully:
              </p>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Processed all uploaded documents</li>
                <li>• Generated searchable content chunks</li>
                <li>• Created structured wiki documentation</li>
                <li>• Made content available for public viewing</li>
              </ul>
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md dark:bg-green-900/20 dark:border-green-700/50">
                <p className="text-sm text-green-800 dark:text-green-300">
                  <strong>Status:</strong> All processing stages completed successfully. 
                  The project wiki and content are now available for exploration.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}