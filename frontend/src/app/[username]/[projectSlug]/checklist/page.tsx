import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import ProjectChecklistContent from '@/components/features/project-pages/ProjectChecklistContent';
import { Skeleton } from '@/components/ui/skeleton';

interface ProjectChecklistPageProps {
  params: Promise<{
    username: string;
    projectSlug: string;
  }>;
}

export async function generateMetadata({ params }: ProjectChecklistPageProps) {
  const { username, projectSlug } = await params;

  return {
    title: `Checklist - ${username}/${projectSlug}`,
  };
}

async function UnifiedProjectChecklistContent({
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

    // Get the latest indexing run ID for this project using GitHub-style API
    let indexingRunId: string | null = null;

    try {
      // Use GitHub-style API to get all runs for this project
      const runsResponse = await apiClient.getProjectRuns(username, projectSlug);
      const runs = runsResponse.runs || [];

      if (runs.length > 0) {
        // Get the latest completed run
        const latestRun = runs.find(run => run.status === 'completed') || runs[0];
        indexingRunId = latestRun.id;
      }
    } catch (error) {
      console.warn('Could not get runs for project, will show no checklist message:', error);
    }

    // If no indexing run found, return no checklist message
    if (!indexingRunId) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Checklist Not Available</h2>
          <p className="text-muted-foreground">
            This project doesn't have a completed indexing run yet.
          </p>
        </div>
      );
    }

    // Determine if this is an anonymous project (public access)
    const isAuthenticated = username !== 'anonymous';

    return (
      <ProjectChecklistContent
        projectSlug={`${username}/${projectSlug}`}
        runId={indexingRunId}
        isAuthenticated={isAuthenticated}
        user={isAuthenticated ? { username } : null}
      />
    );
  } catch (error) {
    console.error('Error loading unified project checklist:', error);

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

function ChecklistLoadingSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <Skeleton className="h-6 w-1/3 mb-4" />
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      <div className="bg-card border border-border rounded-lg p-6">
        <Skeleton className="h-6 w-1/4 mb-4" />
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
      <div className="flex justify-center">
        <Skeleton className="h-10 w-32" />
      </div>
    </div>
  );
}

export default async function ProjectChecklistPage({ params }: ProjectChecklistPageProps) {
  const { username, projectSlug } = await params;

  return (
    <Suspense fallback={<ChecklistLoadingSkeleton />}>
      <UnifiedProjectChecklistContent username={username} projectSlug={projectSlug} />
    </Suspense>
  );
}