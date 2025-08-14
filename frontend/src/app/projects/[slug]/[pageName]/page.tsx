import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { apiClient, WikiPage, type WikiPageContent } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';
import WikiLayoutSkeleton from '@/components/features/wiki/WikiLayoutSkeleton';
import { Skeleton } from '@/components/ui/skeleton';

interface WikiPageProps {
  params: Promise<{
    slug: string;
    pageName: string;
  }>;
}

// Component to load pages data first, then show smart skeleton while content loads
async function WikiPageWithSmartSkeleton({ slug, pageName }: { slug: string; pageName: string }) {
  try {
    // Get project details and pages data first (for stable sidebar)
    const project = await apiClient.getProjectFromSlug(slug);
    const wikiRuns = await apiClient.getWikiRunsByIndexingRun(project.id);
    const completedWikiRun = wikiRuns.find((run: any) => run.status === 'completed');
    
    if (!completedWikiRun) {
      notFound();
    }

    const wikiPagesResponse = await apiClient.getWikiPages(completedWikiRun.id);
    const backendPages = wikiPagesResponse.pages || [];
    const sortedPages = backendPages
      .sort((a: any, b: any) => a.order - b.order)
      .map((page: any) => ({
        ...page,
        name: page.filename.replace('.md', '')
      }));

    // Verify the requested page exists
    const requestedPage = sortedPages.find((page: any) => page.name === pageName);
    if (!requestedPage) {
      notFound();
    }

    // Now show smart skeleton while content loads
    return (
      <Suspense fallback={
        <WikiLayoutSkeleton 
          pages={sortedPages} 
          projectSlug={slug} 
          currentPage={pageName}
        />
      }>
        <WikiPageContent slug={slug} pageName={pageName} pages={sortedPages} wikiRunId={completedWikiRun.id} />
      </Suspense>
    );
  } catch (error) {
    console.error('Error loading wiki page structure:', error);
    notFound();
  }
}

// Component to load just the page content (pages already loaded)
async function WikiPageContent({ 
  slug, 
  pageName, 
  pages, 
  wikiRunId 
}: { 
  slug: string; 
  pageName: string; 
  pages: WikiPage[]; 
  wikiRunId: string;
}) {
  try {
    // Only load the page content now
    const pageContent = await apiClient.getWikiPageContent(wikiRunId, pageName);

    return (
      <WikiLayout 
        pages={pages}
        projectSlug={slug}
        content={pageContent.content}
        currentPage={pageName}
      >
        <LazyWikiContent content={pageContent} />
      </WikiLayout>
    );
  } catch (error) {
    console.error('Error loading wiki page content:', error);
    notFound();
  }
}

function WikiPageLoadingSkeleton() {
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

export default async function WikiPageRoute({ params }: WikiPageProps) {
  const { slug, pageName } = await params;
  
  return (
    <Suspense fallback={<WikiPageLoadingSkeleton />}>
      <WikiPageWithSmartSkeleton slug={slug} pageName={pageName} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour
export const dynamicParams = true; // Allow dynamic params for pages not pre-built