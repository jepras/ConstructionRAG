import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { apiClient, WikiPage, WikiPageContent } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import WikiContent from '@/components/features/wiki/WikiContent';
import { Skeleton } from '@/components/ui/skeleton';

interface WikiPageProps {
  params: Promise<{
    slug: string;
    pageName: string;
  }>;
}

async function WikiPageContent({ slug, pageName }: { slug: string; pageName: string }) {
  try {
    // Get project details (indexing run)
    const project = await apiClient.getProjectFromSlug(slug);
    
    // Get wiki runs for this indexing run
    const wikiRuns = await apiClient.getWikiRunsByIndexingRun(project.id);
    
    // Find the first completed wiki run
    const completedWikiRun = wikiRuns.find(run => run.status === 'completed');
    
    if (!completedWikiRun) {
      notFound();
    }

    // Get wiki pages and specific page content
    const [wikiPagesResponse, pageContent] = await Promise.all([
      apiClient.getWikiPages(completedWikiRun.id),
      apiClient.getWikiPageContent(completedWikiRun.id, pageName)
    ]);

    // Extract and format pages
    const backendPages = wikiPagesResponse.pages || [];
    const sortedPages = backendPages
      .sort((a, b) => a.order - b.order)
      .map(page => ({
        ...page,
        name: page.filename.replace('.md', '')
      }));

    // Verify the requested page exists
    const requestedPage = sortedPages.find(page => page.name === pageName);
    if (!requestedPage) {
      notFound();
    }

    return (
      <WikiLayout 
        pages={sortedPages}
        projectSlug={slug}
        content={pageContent.content}
        currentPage={pageName}
      >
        <WikiContent content={pageContent} />
      </WikiLayout>
    );
  } catch (error) {
    console.error('Error loading wiki page:', error);
    notFound();
  }
}

function WikiPageLoadingSkeleton() {
  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar skeleton */}
      <div className="hidden lg:block w-64 bg-background border-r border-border">
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
      <div className="hidden xl:block w-64 bg-background border-l border-border">
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
    <div className="min-h-screen bg-background">
      <Suspense fallback={<WikiPageLoadingSkeleton />}>
        <WikiPageContent slug={slug} pageName={pageName} />
      </Suspense>
    </div>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = false;