'use client';

import { useEffect, useState } from 'react';
import { notFound } from 'next/navigation';
import { WikiPage } from '@/lib/api-client';
import {
  useProjectBasic,
  useProjectWikiRuns,
  useProjectWikiPages,
  useProjectWikiContent,
} from '@/hooks/useApiQueries';
import WikiLayout from './WikiLayout';
import WikiContent from './WikiContent';
import { Skeleton } from '@/components/ui/skeleton';

interface ProjectWikiClientProps {
  slug: string;
  // Optimistic data from project card (for immediate display)
  optimisticData?: {
    title?: string;
    description?: string;
  };
}

function ProgressiveWikiLoadingSkeleton({ 
  hasProjectData, 
  hasWikiStructure, 
  projectTitle 
}: { 
  hasProjectData: boolean;
  hasWikiStructure: boolean;
  projectTitle?: string;
}) {
  return (
    <div className="flex h-full">
      {/* Sidebar skeleton */}
      <div className="hidden lg:block w-64 border-r border-border">
        <div className="p-4 space-y-4">
          {hasWikiStructure ? (
            <>
              <div className="h-6 w-32 bg-muted-foreground/20 rounded flex items-center text-sm">
                <h3 className="text-sm font-semibold text-foreground mb-4 uppercase tracking-wide pt-6 sticky top-0 bg-card">
                  Sections
                </h3>
              </div>
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            </>
          ) : (
            <>
              <Skeleton className="h-6 w-32" />
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            </>
          )}
        </div>
      </div>
      
      {/* Content skeleton */}
      <div className="flex-1 min-w-0">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {hasProjectData && projectTitle ? (
            <h1 className="text-3xl font-bold text-foreground mb-4">
              {projectTitle}
            </h1>
          ) : (
            <Skeleton className="h-10 w-3/4 mb-4" />
          )}
          <Skeleton className="h-4 w-1/2 mb-8" />
          <div className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      </div>
      
      {/* TOC skeleton */}
      <div className="hidden xl:block w-64 border-l border-border">
        <div className="p-4 space-y-2">
          <Skeleton className="h-5 w-24" />
          <div className="space-y-1">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-5/6" />
            <Skeleton className="h-6 w-4/5" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProjectWikiClient({ slug, optimisticData }: ProjectWikiClientProps) {
  const [loadingStage, setLoadingStage] = useState<'project' | 'wiki-runs' | 'pages' | 'content' | 'complete'>('project');

  // Progressive data loading
  const {
    data: project,
    isLoading: isLoadingProject,
    error: projectError,
  } = useProjectBasic(slug);

  const {
    data: wikiRuns,
    isLoading: isLoadingWikiRuns,
    error: wikiRunsError,
  } = useProjectWikiRuns(project?.id || null, !!project);

  // Find completed wiki run
  const completedWikiRun = wikiRuns?.find((run: any) => run.status === 'completed');

  const {
    data: wikiPagesResponse,
    isLoading: isLoadingPages,
    error: pagesError,
  } = useProjectWikiPages(completedWikiRun?.id || null, !!completedWikiRun);

  // Get sorted pages
  const sortedPages = wikiPagesResponse?.pages
    ?.sort((a: any, b: any) => a.order - b.order)
    .map((page: any) => ({
      ...page,
      name: page.filename.replace('.md', ''), // Add name field for compatibility
    })) || [];

  const firstPage = sortedPages[0];

  const {
    data: firstPageContent,
    isLoading: isLoadingContent,
    error: contentError,
  } = useProjectWikiContent(
    completedWikiRun?.id || null,
    firstPage?.name || null,
    !!completedWikiRun && !!firstPage
  );

  // Update loading stage based on data availability
  useEffect(() => {
    if (project && !isLoadingProject) {
      setLoadingStage('wiki-runs');
    }
    if (wikiRuns && !isLoadingWikiRuns) {
      setLoadingStage('pages');
    }
    if (wikiPagesResponse && !isLoadingPages) {
      setLoadingStage('content');
    }
    if (firstPageContent && !isLoadingContent) {
      setLoadingStage('complete');
    }
  }, [project, wikiRuns, wikiPagesResponse, firstPageContent, isLoadingProject, isLoadingWikiRuns, isLoadingPages, isLoadingContent]);

  // Handle errors
  if (projectError || wikiRunsError || pagesError || contentError) {
    console.error('Error loading project wiki:', { projectError, wikiRunsError, pagesError, contentError });
    notFound();
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

  // Show progressive loading skeleton
  if (loadingStage !== 'complete' || !firstPageContent) {
    const projectTitle = project?.name || optimisticData?.title;
    return (
      <ProgressiveWikiLoadingSkeleton
        hasProjectData={!!project}
        hasWikiStructure={!!wikiPagesResponse}
        projectTitle={projectTitle}
      />
    );
  }

  // Render complete wiki
  return (
    <WikiLayout 
      pages={sortedPages as WikiPage[]}
      projectSlug={slug}
      content={firstPageContent?.content || ''}
      currentPage={firstPage?.name || ''}
    >
      <WikiContent content={firstPageContent!} />
    </WikiLayout>
  );
}