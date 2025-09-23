import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import QueryLayout from '@/components/features/query/QueryLayout';
import { Skeleton } from '@/components/ui/skeleton';

interface UnifiedProjectQueryPageProps {
  params: Promise<{
    username: string;
    projectSlug: string;
  }>;
}

export async function generateMetadata({ params }: UnifiedProjectQueryPageProps) {
  return {
    title: "Query",
  };
}

async function UnifiedProjectQueryContent({
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
      <QueryLayout
        indexingRunId={indexingRunId}
        projectSlug={`${username}/${projectSlug}`}
      />
    );
  } catch (error) {
    console.error('Error loading unified project query:', error);

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

function QueryLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <Skeleton className="h-10 w-1/3 mb-8" />
        <div className="space-y-4 mb-8">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="space-y-4">
          <Skeleton className="h-6 w-1/4" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    </div>
  );
}

export default async function UnifiedProjectQueryPage({ params }: UnifiedProjectQueryPageProps) {
  const { username, projectSlug } = await params;

  return (
    <Suspense fallback={<QueryLoadingSkeleton />}>
      <UnifiedProjectQueryContent username={username} projectSlug={projectSlug} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour