'use client';

import React, { ReactNode } from 'react';
import { Header } from '@/components/layout/Header';
import ProjectHeader from '@/components/layout/ProjectHeader';
import { useAuth } from '@/components/providers/AuthProvider';

interface UnifiedProjectLayoutProps {
  children: ReactNode;
  params: Promise<{ username: string; projectSlug: string }>;
}

function UnifiedProjectLayoutContent({ children, params }: UnifiedProjectLayoutProps) {
  const { isAuthenticated } = useAuth();

  // Handle params properly in client component
  const [projectInfo, setProjectInfo] = React.useState<{ username: string; projectSlug: string } | null>(null);

  React.useEffect(() => {
    params.then(({ username, projectSlug }) => {
      setProjectInfo({ username, projectSlug });
    });
  }, [params]);

  // Use project slug as display name initially, will be updated by API call
  const displayName = projectInfo ? `${projectInfo.username}/${projectInfo.projectSlug}` : "Loading...";

  // For unified projects, use the GitHub-style slug
  const projectSlug = projectInfo ? `${projectInfo.username}/${projectInfo.projectSlug}` : '';

  return (
    <div className="min-h-screen bg-background">
      <Header variant={isAuthenticated ? "app" : "marketing"} />
      {projectInfo && (
        <ProjectHeader
          projectSlug={projectSlug}
          projectName={displayName}
          runId={null} // Unified projects don't show specific run ID in header
        />
      )}
      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          <div className="bg-card border border-border rounded-lg shadow-sm">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}

export default function UnifiedProjectLayout({ children, params }: UnifiedProjectLayoutProps) {
  return (
    <UnifiedProjectLayoutContent children={children} params={params} />
  );
}