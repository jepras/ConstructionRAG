import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';
import { Skeleton } from '@/components/ui/skeleton';

interface PublicWikiPageProps {
  params: Promise<{
    indexingRunId: string;
    pageName: string;
  }>;
  searchParams?: Promise<{ [key: string]: string | string[] | undefined }>;
}

// Extract UUID from slug format: "project-name-{uuid}"
function extractUUIDFromSlug(slug: string): string {
  const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const match = slug.match(uuidRegex);
  if (!match) {
    throw new Error(`Invalid slug format, no UUID found: ${slug}`);
  }
  return match[0];
}

async function PublicWikiPageContent({ 
  indexingRunId, 
  pageName 
}: { 
  indexingRunId: string; 
  pageName: string; 
}) {
  try {
    // Extract the actual UUID from the slug
    const actualRunId = extractUUIDFromSlug(indexingRunId);
    
    // Get wiki runs for this indexing run
    const wikiRuns = await apiClient.getWikiRunsByIndexingRun(actualRunId);
    
    // Find the first completed wiki run
    const completedWikiRun = wikiRuns.find(run => run.status === 'completed');
    
    if (!completedWikiRun) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Not Available</h2>
          <p className="text-muted-foreground">
            This project doesn't have a wiki generated yet.
          </p>
        </div>
      );
    }

    // Get wiki pages for the completed wiki run
    const wikiPagesResponse = await apiClient.getWikiPages(completedWikiRun.id);
    
    // Extract pages array from response and sort by order
    const backendPages = wikiPagesResponse.pages || [];
    if (backendPages.length === 0) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Wiki Pages Not Found</h2>
          <p className="text-muted-foreground">
            No wiki pages are available for this project.
          </p>
        </div>
      );
    }
    
    // Sort pages by order and map to expected format
    const sortedPages = backendPages
      .sort((a, b) => a.order - b.order)
      .map(page => ({
        ...page,
        name: page.filename.replace('.md', '') // Add name field for compatibility
      }));
    
    // Check if the requested page exists
    const requestedPage = sortedPages.find(page => page.name === pageName);
    if (!requestedPage) {
      return (
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
          <p className="text-muted-foreground">
            The requested wiki page "{pageName}" could not be found.
          </p>
        </div>
      );
    }

    // Get content for the requested page
    const pageContent = await apiClient.getWikiPageContent(completedWikiRun.id, pageName);

    // For single-slug public projects, use the indexing run ID as the project slug
    const navigationSlug = indexingRunId;

    return (
      <WikiLayout 
        pages={sortedPages}
        projectSlug={navigationSlug}
        content={pageContent.content}
        currentPage={pageName}
      >
        <LazyWikiContent content={pageContent} />
      </WikiLayout>
    );
  } catch (error) {
    console.error('Error loading public wiki page:', error);
    
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Page Not Found</h2>
        <p className="text-muted-foreground">
          The requested wiki page could not be found or is not available.
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

export default async function PublicWikiPage({ params, searchParams }: PublicWikiPageProps) {
  const { indexingRunId, pageName } = await params;
  
  return (
    <Suspense fallback={<WikiLoadingSkeleton />}>
      <PublicWikiPageContent indexingRunId={indexingRunId} pageName={pageName} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour