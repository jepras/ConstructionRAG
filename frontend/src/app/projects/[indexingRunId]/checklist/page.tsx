'use client';

import React, { useEffect } from 'react';
import { useAuth } from '@/components/providers/AuthProvider';
import ProjectChecklistContent from '@/components/features/project-pages/ProjectChecklistContent';

interface PublicProjectChecklistPageProps {
  params: Promise<{
    indexingRunId: string;
  }>;
}

export default function PublicProjectChecklistPage({ params }: PublicProjectChecklistPageProps) {
  const { user, isAuthenticated } = useAuth();

  // Handle params for client component
  const [indexingRunId, setIndexingRunId] = React.useState<string>('');

  React.useEffect(() => {
    params.then(({ indexingRunId }) => {
      setIndexingRunId(indexingRunId);
    });
  }, [params]);

  useEffect(() => {
    document.title = "Checklist - specfinder.io";
  }, []);

  // Don't render until we have the params
  if (!indexingRunId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <ProjectChecklistContent 
      projectSlug={indexingRunId}
      runId={indexingRunId}
      isAuthenticated={isAuthenticated}
      user={user}
    />
  );
}