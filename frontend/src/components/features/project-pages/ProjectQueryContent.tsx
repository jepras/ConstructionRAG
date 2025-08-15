'use client';

import React from 'react';

interface ProjectQueryContentProps {
  projectSlug: string;
  runId: string;
  isAuthenticated: boolean;
  user?: any | null;
}

export default function ProjectQueryContent({ 
  projectSlug, 
  runId, 
  isAuthenticated, 
  user 
}: ProjectQueryContentProps) {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Project Q&A</h1>
        <p className="text-muted-foreground">
          {isAuthenticated 
            ? "Ask questions about your project documentation and get AI-powered answers."
            : "Ask questions about this project's documentation and get AI-powered answers."
          }
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <div className="text-center py-12">
          <div className="mb-4">
            <div className="mx-auto w-16 h-16 bg-muted rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-4">
            {isAuthenticated ? "Q&A Feature Coming Soon" : "Q&A Interface"}
          </h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            {isAuthenticated 
              ? "The Q&A interface for private projects is currently under development. You'll be able to ask questions about your project documentation and get instant AI-powered answers."
              : "The Q&A feature for this project allows you to ask questions about the documentation and receive AI-powered answers based on the content."
            }
          </p>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>• Context-aware responses from {isAuthenticated ? 'your' : 'project'} documents</p>
            <p>• {isAuthenticated ? 'Conversation history' : 'Source citations and references'}</p>
            <p>• {isAuthenticated ? 'Source citations and references' : 'Natural language processing'}</p>
          </div>

          {/* Context-specific messaging */}
          {isAuthenticated ? (
            <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-md dark:bg-yellow-900/20 dark:border-yellow-700/50">
              <p className="text-sm text-yellow-800 dark:text-yellow-300">
                <strong>Development Status:</strong> Interactive Q&A features are being developed specifically for authenticated project owners.
              </p>
            </div>
          ) : (
            <div className="mt-8 p-4 bg-muted/30 rounded-md">
              <p className="text-sm text-muted-foreground">
                <strong>Note:</strong> This is a read-only view of the project. 
                Interactive Q&A features require authentication.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Project Context Information */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-semibold text-foreground mb-2">Project Context</h3>
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>ID: {projectSlug}</p>
            <p>Run: {runId}</p>
            <p>Access: {isAuthenticated ? 'Private' : 'Public'}</p>
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-semibold text-foreground mb-2">Available Features</h3>
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>✓ Wiki documentation</p>
            <p>✓ Project information</p>
            <p>{isAuthenticated ? '⏳' : '○'} Interactive Q&A</p>
          </div>
        </div>
      </div>
    </div>
  );
}