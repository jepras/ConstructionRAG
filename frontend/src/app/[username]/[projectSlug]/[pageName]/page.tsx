import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';
import { Skeleton } from '@/components/ui/skeleton';

interface UnifiedProjectWikiPageProps {
  params: Promise<{
    username: string;
    projectSlug: string;
    pageName: string;
  }>;
}

export async function generateMetadata({ params }: UnifiedProjectWikiPageProps) {
  const { username, projectSlug, pageName } = await params;

  try {
    // Get wiki data to find the actual page title
    const wikiData = await apiClient.getProjectWiki(username, projectSlug);
    const currentPage = wikiData.wiki_pages?.find((page: any) => page.name === pageName);

    if (currentPage?.title) {
      return {
        title: `${currentPage.title} - Wiki`,
      };
    }
  } catch (error) {
    console.warn('Could not fetch page title for metadata:', error);
  }

  // Fallback to page name
  return {
    title: `${pageName.charAt(0).toUpperCase() + pageName.slice(1)} - Wiki`,
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

async function UnifiedProjectWikiPageContent({
  username,
  projectSlug,
  pageName
}: {
  username: string;
  projectSlug: string;
  pageName: string;
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

    // Pages already come with correct name field (page-1, page-2, etc.) from the API
    // No need to modify the name field as it's already the clean page ID
    const sortedPages = wikiData.wiki_pages;

    // Find the requested page by matching the URL pageName to the page name
    const currentPage = sortedPages.find(page => page.name === pageName);
    if (!currentPage) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
          <p className="text-muted-foreground">
            The requested wiki page could not be found.
          </p>
        </div>
      );
    }

    // Get the specific page content
    const pageContent = await apiClient.getWikiPageContent(wikiData.wiki_run.id, currentPage.filename);

    // Remove duplicate H1 heading if it matches the page title
    let contentToDisplay = pageContent;
    if (contentToDisplay.content && contentToDisplay.title) {
      const h1Pattern = new RegExp(`^#\\s+${contentToDisplay.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n`, 'i');
      contentToDisplay = {
        ...contentToDisplay,
        content: contentToDisplay.content.replace(h1Pattern, '')
      };
    }

    // Extract title from metadata (unified API structure is different)
    const wikiTitle = wikiData.metadata?.wiki_structure?.title || project.name || 'Project';

    // Use unified slug format for navigation
    const navigationSlug = `${username}/${projectSlug}`;

    return (
      <WikiLayout
        pages={sortedPages}
        projectSlug={navigationSlug}
        content={contentToDisplay.content}
        currentPage={pageName}
      >
        <LazyWikiContent
          content={contentToDisplay}
          showSummaryBar={true}
          indexingRunId={indexingRunId}
        />
      </WikiLayout>
    );
  } catch (error) {
    console.error('Error loading unified project wiki page:', error);

    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
        <p className="text-muted-foreground">
          The requested wiki page could not be found or you don't have access to it.
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

export default async function UnifiedProjectWikiPage({ params }: UnifiedProjectWikiPageProps) {
  const { username, projectSlug, pageName } = await params;

  return (
    <Suspense fallback={<WikiLoadingSkeleton />}>
      <UnifiedProjectWikiPageContent
        username={username}
        projectSlug={projectSlug}
        pageName={pageName}
      />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour