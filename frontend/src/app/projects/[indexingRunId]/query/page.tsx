import { Suspense } from 'react';
import ProjectQueryContent from '@/components/features/project-pages/ProjectQueryContent';

interface PublicProjectQueryPageProps {
  params: Promise<{
    indexingRunId: string;
  }>;
}

export async function generateMetadata({ params }: PublicProjectQueryPageProps) {
  return {
    title: "Q&A",
  };
}

async function PublicProjectQueryWrapper({ indexingRunId }: { indexingRunId: string }) {
  return (
    <ProjectQueryContent 
      projectSlug={indexingRunId}  // Use run ID as slug for public projects
      runId={indexingRunId}
      isAuthenticated={false}
      user={null}
    />
  );
}

export default async function PublicProjectQueryPage({ params }: PublicProjectQueryPageProps) {
  const { indexingRunId } = await params;
  
  return (
    <Suspense fallback={
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-muted rounded w-1/3"></div>
          <div className="bg-card border border-border rounded-lg p-6">
            <div className="space-y-4">
              <div className="h-4 bg-muted rounded w-1/2 mx-auto"></div>
              <div className="h-4 bg-muted rounded w-1/3 mx-auto"></div>
            </div>
          </div>
        </div>
      </div>
    }>
      <PublicProjectQueryWrapper indexingRunId={indexingRunId} />
    </Suspense>
  );
}

// Enable ISR
export const revalidate = 3600;