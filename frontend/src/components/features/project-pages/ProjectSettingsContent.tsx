'use client';

import React from 'react';

interface ProjectSettingsContentProps {
  projectSlug: string;
  runId: string;
  isAuthenticated: boolean;
  user?: any | null;
}

export default function ProjectSettingsContent({ 
  projectSlug, 
  runId, 
  isAuthenticated, 
  user 
}: ProjectSettingsContentProps) {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Project Settings</h1>
        <p className="text-muted-foreground">
          {isAuthenticated 
            ? "Manage your project configuration and preferences."
            : "View project configuration and information."
          }
        </p>
      </div>

      <div className="space-y-8">
        {/* Project Information Section */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Project Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {isAuthenticated ? "Project Slug" : "Project Identifier"}
              </label>
              <input
                type="text"
                value={projectSlug}
                readOnly
                className="w-full px-3 py-2 bg-muted border border-border rounded-md text-foreground"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {isAuthenticated ? "Current Run ID" : "Indexing Run ID"}
              </label>
              <input
                type="text"
                value={runId}
                readOnly
                className="w-full px-3 py-2 bg-muted border border-border rounded-md text-foreground"
              />
            </div>
          </div>
        </div>

        {/* Access Control Section */}
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Access Control</h2>
          <p className="text-muted-foreground mb-4">
            {isAuthenticated 
              ? "This is a private project accessible only to authenticated users."
              : "This is a public project accessible to everyone."
            }
          </p>
          <div className="bg-muted/50 border border-border rounded-md p-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isAuthenticated ? 'bg-green-500' : 'bg-blue-500'}`}></div>
              <span className="text-sm font-medium text-foreground">
                {isAuthenticated ? "Private Project" : "Public Project"}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {isAuthenticated 
                ? "Only you can access this project and its wiki content."
                : "Anyone with the link can view this project and its wiki content."
              }
            </p>
          </div>
        </div>

        {/* Context-specific sections */}
        {isAuthenticated ? (
          /* Private Project Features */
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-xl font-semibold text-foreground mb-4">Additional Settings</h2>
            <p className="text-muted-foreground">
              More configuration options will be available in future updates, including:
            </p>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              <li>• Project name and description editing</li>
              <li>• Wiki generation preferences</li>
              <li>• Export options</li>
              <li>• Collaboration settings</li>
            </ul>
          </div>
        ) : (
          /* Public Project Information */
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-xl font-semibold text-foreground mb-4">Public Access</h2>
            <p className="text-muted-foreground mb-3">
              This project has been processed and made publicly available. Anyone with the link can:
            </p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>• View the generated wiki documentation</li>
              <li>• Browse through all project pages</li>
              <li>• Access the structured content</li>
            </ul>
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md dark:bg-blue-900/20 dark:border-blue-700/50">
              <p className="text-sm text-blue-800 dark:text-blue-300">
                <strong>Note:</strong> Advanced project management features 
                are available for authenticated project owners.
              </p>
            </div>
          </div>
        )}

        {/* User Information for authenticated users */}
        {isAuthenticated && user && (
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-xl font-semibold text-foreground mb-4">Owner Information</h2>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-foreground">User ID</span>
                <span className="text-sm text-muted-foreground font-mono">{user.id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-foreground">Email</span>
                <span className="text-sm text-muted-foreground">{user.email}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}