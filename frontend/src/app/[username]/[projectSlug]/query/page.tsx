import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import ProjectQueryContent from '@/components/features/project-pages/ProjectQueryContent';
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

    // Determine if this is an anonymous project (public access)
    const isAuthenticated = username !== 'anonymous';

    // Debug logging
    console.log('🔍 Query page debug:', {
      username,
      projectSlug,
      project,
      indexingRunId,
      isAuthenticated,
      combinedProjectSlug: `${username}/${projectSlug}`
    });

    return (
      <ProjectQueryContent
        projectSlug={`${username}/${projectSlug}`}
        runId={indexingRunId}
        isAuthenticated={isAuthenticated}
        user={isAuthenticated ? { username } : null}
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
    <div className="grid grid-cols-1 lg:grid-cols-2 lg:grid-rows-1 h-[calc(100vh-16rem)] lg:h-[calc(100vh-15rem)]">
      {/* Left Side Skeleton - Query Interface */}
      <div className="min-w-0 flex flex-col col-span-1 lg:min-h-0">
        <div className="px-6 py-4 border-b border-border flex-shrink-0">
          <Skeleton className="h-8 w-1/3 mb-2" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <div className="flex-1 p-6 space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-10 w-24" />
          <div className="space-y-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </div>

      {/* Right Side Skeleton - Source Panel */}
      <div className="hidden lg:block col-span-1 border-l border-border">
        <div className="p-6 space-y-4">
          <Skeleton className="h-6 w-1/3" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
          <Skeleton className="h-32 w-full" />
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