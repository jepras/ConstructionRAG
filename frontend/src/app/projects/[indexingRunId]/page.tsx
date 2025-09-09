import { Suspense } from 'react';
import { apiClient } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';
import ProjectWikiClient from '@/components/features/wiki/ProjectWikiClient';
import WikiTitleSetter from '@/components/features/wiki/WikiTitleSetter';
import { Skeleton } from '@/components/ui/skeleton';

interface PublicProjectPageProps {
  params: Promise<{ indexingRunId: string }>;
  searchParams?: Promise<{ [key: string]: string | string[] | undefined }>;
}

export async function generateMetadata({ params }: PublicProjectPageProps) {
  return {
    title: "Wiki",
  };
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

// Extract wiki title from metadata
function extractWikiTitle(metadata: any): string {
  try {
    return metadata?.metadata?.wiki_structure?.title || 'Project';
  } catch {
    return 'Project';
  }
}

async function PublicProjectWikiContent({ indexingRunId }: { indexingRunId: string }) {
  try {
    // Extract the actual UUID from the slug
    const actualRunId = extractUUIDFromSlug(indexingRunId);
    
    // Get all wiki data in one batched call
    const wikiData = await apiClient.getWikiInitialData(actualRunId);
    
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

    if (wikiData.pages.length === 0) {
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
    const sortedPages = wikiData.pages.map(page => ({
      ...page,
      name: page.filename.replace('.md', '') // Add name field for compatibility
    }));
    
    const firstPage = sortedPages[0];
    const firstPageContent = wikiData.first_page_content;

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

    // Extract title from metadata
    const wikiTitle = extractWikiTitle(wikiData.metadata);

    // For single-slug public projects, use the indexing run ID as both slug and runId
    const navigationSlug = indexingRunId;

    return (
      <>
        <WikiTitleSetter title={wikiTitle} />
        <WikiLayout 
          pages={sortedPages}
          projectSlug={navigationSlug}
          content={contentToDisplay.content}
          currentPage={firstPage.name}
        >
          <LazyWikiContent content={contentToDisplay} />
        </WikiLayout>
      </>
    );
  } catch (error) {
    console.error('Error loading public project wiki:', error);
    
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-foreground mb-4">Project Not Found</h2>
        <p className="text-muted-foreground">
          The requested project could not be found or is not available.
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

export default async function PublicProjectPage({ params }: PublicProjectPageProps) {
  const { indexingRunId } = await params;
  
  // Always use server-side rendering for public projects (better SEO)
  return (
    <Suspense fallback={<WikiLoadingSkeleton />}>
      <PublicProjectWikiContent indexingRunId={indexingRunId} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour