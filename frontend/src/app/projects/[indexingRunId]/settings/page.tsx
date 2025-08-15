import { Suspense } from 'react';
import ProjectSettingsContent from '@/components/features/project-pages/ProjectSettingsContent';

interface PublicProjectSettingsPageProps {
  params: Promise<{
    indexingRunId: string;
  }>;
}

async function PublicProjectSettingsWrapper({ indexingRunId }: { indexingRunId: string }) {
  return (
    <ProjectSettingsContent 
      projectSlug={indexingRunId}  // Use run ID as slug for public projects
      runId={indexingRunId}
      isAuthenticated={false}
      user={null}
    />
  );
}

export default async function PublicProjectSettingsPage({ params }: PublicProjectSettingsPageProps) {
  const { indexingRunId } = await params;
  
  return (
    <Suspense fallback={
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-muted rounded w-1/3"></div>
          <div className="space-y-4">
            <div className="h-4 bg-muted rounded w-1/2"></div>
            <div className="h-4 bg-muted rounded w-1/4"></div>
          </div>
        </div>
      </div>
    }>
      <PublicProjectSettingsWrapper indexingRunId={indexingRunId} />
    </Suspense>
  );
}

// Enable ISR
export const revalidate = 3600;