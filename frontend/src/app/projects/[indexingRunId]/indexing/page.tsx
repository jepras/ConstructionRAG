import { Suspense } from 'react';
import ProjectIndexingContent from '@/components/features/project-pages/ProjectIndexingContent';

interface PublicProjectIndexingPageProps {
  params: Promise<{
    indexingRunId: string;
  }>;
}

async function PublicProjectIndexingWrapper({ indexingRunId }: { indexingRunId: string }) {
  return (
    <ProjectIndexingContent 
      projectSlug={indexingRunId}  // Use run ID as slug for public projects
      runId={indexingRunId}
      isAuthenticated={false}
      user={null}
    />
  );
}

export default async function PublicProjectIndexingPage({ params }: PublicProjectIndexingPageProps) {
  const { indexingRunId } = await params;
  
  return (
    <Suspense fallback={
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-muted rounded w-1/3"></div>
          <div className="space-y-4">
            <div className="h-32 bg-muted rounded"></div>
            <div className="h-48 bg-muted rounded"></div>
          </div>
        </div>
      </div>
    }>
      <PublicProjectIndexingWrapper indexingRunId={indexingRunId} />
    </Suspense>
  );
}

// Enable ISR
export const revalidate = 3600;