'use client';

import React from 'react';
import { useAuth } from '@/components/providers/AuthProvider';
import { useProjectWithRun, useProjectWikiRuns, useProjectWikiPages, useProjectWikiContent } from '@/hooks/useApiQueries';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';

interface DashboardWikiPageProps {
  params: Promise<{
    projectSlug: string;
    runId: string;
    pageName: string;
  }>;
}

// Extract project ID from projectSlug format: "project-name-{project_id}"
function extractProjectIdFromSlug(projectSlug: string): string | null {
  const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const match = projectSlug.match(uuidRegex);
  return match ? match[0] : null;
}

export default function DashboardWikiPage({ params }: DashboardWikiPageProps) {
  const { isAuthenticated, isLoading } = useAuth();

  // Handle params for client component
  const [projectSlug, setProjectSlug] = React.useState<string>('');
  const [runId, setRunId] = React.useState<string>('');
  const [pageName, setPageName] = React.useState<string>('');

  React.useEffect(() => {
    params.then(({ projectSlug, runId, pageName }) => {
      setProjectSlug(projectSlug);
      setRunId(runId);
      setPageName(pageName);
    });
  }, [params]);

  const projectId = extractProjectIdFromSlug(projectSlug);

  // Show loading during auth check
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Auth is handled by (app) route group middleware, but double-check
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Authentication Required</h2>
          <p className="text-muted-foreground">Please sign in to view this wiki page.</p>
        </div>
      </div>
    );
  }

  // Don't render until we have the params
  if (!projectId || !runId || !pageName) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return <WikiPageContent projectId={projectId} runId={runId} pageName={pageName} projectSlug={projectSlug} />;
}

function WikiPageContent({ 
  projectId, 
  runId, 
  pageName, 
  projectSlug 
}: { 
  projectId: string; 
  runId: string; 
  pageName: string; 
  projectSlug: string;
}) {
  // Get project info
  const { data: project, isLoading: isLoadingProject, error: projectError } = useProjectWithRun(projectId, runId);

  // Get wiki runs for this indexing run
  const { data: wikiRuns, isLoading: isLoadingWikiRuns, error: wikiRunsError } = useProjectWikiRuns(runId, !!runId);

  // Find completed wiki run
  const completedWikiRun = wikiRuns?.find((run: any) => run.status === 'completed');

  // Get all wiki pages for navigation
  const { data: wikiPagesResponse, isLoading: isLoadingPages, error: pagesError } = useProjectWikiPages(completedWikiRun?.id || null, !!completedWikiRun);

  // Get sorted pages
  const sortedPages = wikiPagesResponse?.pages
    ?.sort((a: any, b: any) => a.order - b.order)
    .map((page: any) => ({
      ...page,
      name: page.filename.replace('.md', ''), // Add name field for compatibility
    })) || [];

  // Get content for the specific page
  const { data: pageContent, isLoading: isLoadingContent, error: contentError } = useProjectWikiContent(
    completedWikiRun?.id || null,
    pageName,
    !!completedWikiRun && !!pageName
  );

  // Handle errors
  if (projectError || wikiRunsError || pagesError || contentError) {
    console.error('Error loading wiki page:', { projectError, wikiRunsError, pagesError, contentError });
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
        <p className="text-muted-foreground">
          The requested wiki page could not be found or is not available.
        </p>
      </div>
    );
  }

  // Handle no wiki case
  if (project && wikiRuns && !completedWikiRun) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Not Available</h2>
        <p className="text-muted-foreground">
          This project doesn't have a wiki generated yet.
        </p>
      </div>
    );
  }

  // Handle no pages case
  if (completedWikiRun && wikiPagesResponse && sortedPages.length === 0) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Pages Not Found</h2>
        <p className="text-muted-foreground">
          No wiki pages are available for this project.
        </p>
      </div>
    );
  }

  // Show loading skeleton while loading
  if (isLoadingProject || isLoadingWikiRuns || isLoadingPages || isLoadingContent || !pageContent) {
    return (
      <div className="flex h-full">
        {/* Sidebar skeleton */}
        <div className="hidden lg:block w-64 border-r border-border">
          <div className="p-4 space-y-4">
            <div className="h-6 w-32 bg-muted-foreground/20 rounded"></div>
            <div className="space-y-2">
              <div className="h-8 w-full bg-muted-foreground/20 rounded"></div>
              <div className="h-8 w-full bg-muted-foreground/20 rounded"></div>
              <div className="h-8 w-full bg-muted-foreground/20 rounded"></div>
            </div>
          </div>
        </div>
        
        {/* Content skeleton */}
        <div className="flex-1 min-w-0">
          <div className="max-w-4xl mx-auto px-6 py-8">
            <div className="h-10 w-3/4 bg-muted-foreground/20 rounded mb-4"></div>
            <div className="h-4 w-1/2 bg-muted-foreground/20 rounded mb-8"></div>
            <div className="space-y-4">
              <div className="h-4 w-full bg-muted-foreground/20 rounded"></div>
              <div className="h-4 w-full bg-muted-foreground/20 rounded"></div>
              <div className="h-4 w-3/4 bg-muted-foreground/20 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Create navigation slug for compatibility
  const navigationSlug = `${projectSlug}/${runId}`;

  // Render complete wiki page
  return (
    <WikiLayout 
      pages={sortedPages}
      projectSlug={navigationSlug}
      content={pageContent?.content || ''}
      currentPage={pageName}
      isAuthenticated={true}
    >
      <LazyWikiContent content={pageContent!} />
    </WikiLayout>
  );
}