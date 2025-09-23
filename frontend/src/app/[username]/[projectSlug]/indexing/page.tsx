import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import IndexingLayout from '@/components/features/indexing/IndexingLayout';
import { Skeleton } from '@/components/ui/skeleton';

interface UnifiedProjectIndexingPageProps {
  params: Promise<{
    username: string;
    projectSlug: string;
  }>;
}

export async function generateMetadata({ params }: UnifiedProjectIndexingPageProps) {
  return {
    title: "Indexing",
  };
}

async function UnifiedProjectIndexingContent({
  username,
  projectSlug
}: {
  username: string;
  projectSlug: string;
}) {
  try {
    // Use the new unified API endpoint to get project details
    const project = await apiClient.getUnifiedProject(username, projectSlug);

    if (!project || !project.id) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Project Not Found</h2>
          <p className="text-muted-foreground">
            The requested project could not be found or you don't have access to it.
          </p>
        </div>
      );
    }

    // For now, use the project ID as the indexing run ID (will be updated when we have multiple runs)
    const indexingRunId = project.id;

    return (
      <IndexingLayout
        indexingRunId={indexingRunId}
        projectSlug={`${username}/${projectSlug}`}
      />
    );
  } catch (error) {
    console.error('Error loading unified project indexing:', error);

    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Project Not Found</h2>
        <p className="text-muted-foreground">
          The requested project could not be found or you don't have access to it.
        </p>
      </div>
    );
  }
}

function IndexingLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <Skeleton className="h-10 w-1/3 mb-8" />
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-lg p-6">
            <Skeleton className="h-6 w-1/4 mb-4" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-2 w-full" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Skeleton className="h-32 bg-card border border-border rounded-lg" />
            <Skeleton className="h-32 bg-card border border-border rounded-lg" />
            <Skeleton className="h-32 bg-card border border-border rounded-lg" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default async function UnifiedProjectIndexingPage({ params }: UnifiedProjectIndexingPageProps) {
  const { username, projectSlug } = await params;

  return (
    <Suspense fallback={<IndexingLoadingSkeleton />}>
      <UnifiedProjectIndexingContent username={username} projectSlug={projectSlug} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour