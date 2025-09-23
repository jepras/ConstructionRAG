import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';
import WikiTitleSetter from '@/components/features/wiki/WikiTitleSetter';
import { Skeleton } from '@/components/ui/skeleton';

interface UnifiedProjectPageProps {
  params: Promise<{
    username: string;
    projectSlug: string;
  }>;
  searchParams?: Promise<{ [key: string]: string | string[] | undefined }>;
}

export async function generateMetadata({ params }: UnifiedProjectPageProps) {
  return {
    title: "Wiki",
  };
}

// Extract title from metadata
function extractWikiTitle(metadata: any): string {
  try {
    return metadata?.metadata?.wiki_structure?.title || 'Project';
  } catch {
    return 'Project';
  }
}

async function UnifiedProjectWikiContent({
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
      console.warn('Could not get runs for project, will show no wiki message:', error);
    }

    // If no indexing run found, return no wiki message
    if (!indexingRunId) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Not Available</h2>
          <p className="text-muted-foreground">
            This project doesn't have a completed indexing run yet.
          </p>
        </div>
      );
    }

    // Get all wiki data using GitHub-style API
    const wikiData = await apiClient.getProjectWiki(username, projectSlug);

    if (!wikiData.wiki_run) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Not Available</h2>
          <p className="text-muted-foreground">
            This project doesn't have a wiki generated yet.
          </p>
        </div>
      );
    }

    if (!wikiData.wiki_pages || wikiData.wiki_pages.length === 0) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Pages Not Found</h2>
          <p className="text-muted-foreground">
            No wiki pages are available for this project.
          </p>
        </div>
      );
    }

    // Map pages to expected format (add name field for compatibility)
    const sortedPages = wikiData.wiki_pages.map(page => ({
      ...page,
      name: page.filename ? page.filename.replace('.md', '') : page.name // Add name field for compatibility
    }));

    const firstPage = sortedPages[0];
    const firstPageContent = null; // GitHub-style API doesn't include first page content directly

    // Use default content if first page content is not available
    let contentToDisplay = firstPageContent || {
      filename: firstPage.filename,
      title: firstPage.title,
      content: 'Content is loading...',
      storage_path: firstPage.storage_path,
      storage_url: firstPage.storage_url,
    };

    // Remove duplicate H1 heading if it matches the page title
    if (contentToDisplay.content && contentToDisplay.title) {
      const h1Pattern = new RegExp(`^#\\s+${contentToDisplay.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n`, 'i');
      contentToDisplay = {
        ...contentToDisplay,
        content: contentToDisplay.content.replace(h1Pattern, '')
      };
    }

    // Extract title from metadata (GitHub-style API may not have metadata in same format)
    const wikiTitle = extractWikiTitle(wikiData.metadata) || project.name;

    // Use unified slug format for navigation
    const navigationSlug = `${username}/${projectSlug}`;

    return (
      <>
        <WikiTitleSetter title={wikiTitle} />
        <WikiLayout
          pages={sortedPages}
          projectSlug={navigationSlug}
          content={contentToDisplay.content}
          currentPage={firstPage.name}
        >
          <LazyWikiContent
            content={contentToDisplay}
            showSummaryBar={true}
            indexingRunId={indexingRunId}
          />
        </WikiLayout>
      </>
    );
  } catch (error) {
    console.error('Error loading unified project wiki:', error);

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

function WikiLoadingSkeleton() {
  return (
    <div className="flex h-full">
      {/* Sidebar skeleton */}
      <div className="hidden lg:block w-64 border-r border-border">
        <div className="p-4 space-y-4">
          <Skeleton className="h-6 w-32" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        </div>
      </div>

      {/* Content skeleton */}
      <div className="flex-1 min-w-0">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <Skeleton className="h-10 w-3/4 mb-4" />
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

export default async function UnifiedProjectPage({ params }: UnifiedProjectPageProps) {
  const { username, projectSlug } = await params;

  // Server-side rendering for both public and private projects (better SEO and initial load)
  return (
    <Suspense fallback={<WikiLoadingSkeleton />}>
      <UnifiedProjectWikiContent username={username} projectSlug={projectSlug} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour