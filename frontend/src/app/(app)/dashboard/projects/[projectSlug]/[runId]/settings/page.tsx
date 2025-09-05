'use client';

import React, { useEffect } from 'react';
import { useAuth } from '@/components/providers/AuthProvider';
import ProjectSettingsContent from '@/components/features/project-pages/ProjectSettingsContent';

interface DashboardProjectSettingsPageProps {
  params: Promise<{
    projectSlug: string;
    runId: string;
  }>;
}

export default function DashboardProjectSettingsPage({ params }: DashboardProjectSettingsPageProps) {
  const { user, isAuthenticated, isLoading } = useAuth();

  // Handle params for client component
  const [projectSlug, setProjectSlug] = React.useState<string>('');
  const [runId, setRunId] = React.useState<string>('');

  React.useEffect(() => {
    params.then(({ projectSlug, runId }) => {
      setProjectSlug(projectSlug);
      setRunId(runId);
    });
  }, [params]);

  useEffect(() => {
    document.title = "Settings - specfinder.io";
  }, []);

  // Show loading during auth check
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Auth is handled by (app) route group middleware, but double-check
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Authentication Required</h2>
          <p className="text-muted-foreground">Please sign in to view project settings.</p>
        </div>
      </div>
    );
  }

  // Don't render until we have the params
  if (!projectSlug || !runId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <ProjectSettingsContent 
      projectSlug={projectSlug}
      runId={runId}
      isAuthenticated={true}
      user={user}
    />
  );
}