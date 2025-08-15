'use client';

import React, { ReactNode } from 'react';
import ProjectHeader from '@/components/layout/ProjectHeader';

interface DashboardProjectLayoutProps {
  children: ReactNode;
  params: Promise<{
    projectSlug: string;
    runId: string;
  }>;
}

export default function DashboardProjectLayout({ children, params }: DashboardProjectLayoutProps) {
  // Handle params properly in client component
  const [projectSlug, setProjectSlug] = React.useState<string>('');
  const [runId, setRunId] = React.useState<string>('');

  React.useEffect(() => {
    params.then(({ projectSlug, runId }) => {
      setProjectSlug(projectSlug);
      setRunId(runId);
    });
  }, [params]);

  // Extract project name from slug (everything before the UUID)
  const uuidRegex = /-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const projectName = projectSlug.replace(uuidRegex, '').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  // Create combined slug for compatibility with existing ProjectHeader
  const combinedSlug = `${projectSlug}/${runId}`;

  return (
    <>
      <ProjectHeader
        projectSlug={combinedSlug}
        projectName={projectName || "Project"}
        runId={runId}
      />
      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          <div className="bg-card border border-border rounded-lg shadow-sm min-h-[calc(100vh-200px)]">
            {children}
          </div>
        </div>
      </main>
    </>
  );
}