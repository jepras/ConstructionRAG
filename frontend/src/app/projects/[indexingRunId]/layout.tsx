'use client';

import React, { ReactNode } from 'react';
import { Header } from '@/components/layout/Header';
import ProjectHeader from '@/components/layout/ProjectHeader';
import { useAuth } from '@/components/providers/AuthProvider';

interface PublicProjectLayoutProps {
  children: ReactNode;
  params: Promise<{ indexingRunId: string }>;
}

export default function PublicProjectLayout({ children, params }: PublicProjectLayoutProps) {
  const { isAuthenticated } = useAuth();

  // Handle params properly in client component
  const [indexingRunId, setIndexingRunId] = React.useState<string>('');

  React.useEffect(() => {
    params.then(({ indexingRunId }) => {
      setIndexingRunId(indexingRunId);
    });
  }, [params]);

  // Extract a display name from the indexing run ID (first 8 chars for readability)
  const displayName = indexingRunId ? `Project ${indexingRunId.slice(0, 8)}` : "Project";

  // For public projects, use the indexing run ID as the project slug
  const projectSlug = indexingRunId;

  return (
    <div className="min-h-screen bg-background">
      <Header variant={isAuthenticated ? "app" : "marketing"} />
      {indexingRunId && (
        <ProjectHeader
          projectSlug={projectSlug}
          projectName={displayName}
          runId={indexingRunId}
        />
      )}
      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          <div className="bg-card border border-border rounded-lg shadow-sm min-h-[calc(100vh-200px)]">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}