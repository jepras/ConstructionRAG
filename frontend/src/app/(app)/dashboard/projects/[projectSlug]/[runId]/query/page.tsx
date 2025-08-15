'use client';

import React from 'react';
import { useAuth } from '@/components/providers/AuthProvider';
import ProjectQueryContent from '@/components/features/project-pages/ProjectQueryContent';

interface DashboardProjectQueryPageProps {
  params: Promise<{
    projectSlug: string;
    runId: string;
  }>;
}

export default function DashboardProjectQueryPage({ params }: DashboardProjectQueryPageProps) {
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
          <p className="text-muted-foreground">Please sign in to access the Q&A feature.</p>
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
    <ProjectQueryContent 
      projectSlug={projectSlug}
      runId={runId}
      isAuthenticated={true}
      user={user}
    />
  );
}