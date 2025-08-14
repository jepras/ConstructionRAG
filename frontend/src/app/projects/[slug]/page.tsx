import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { apiClient, WikiPage, WikiPageContent } from '@/lib/api-client';
import WikiLayout from '@/components/features/wiki/WikiLayout';
import LazyWikiContent from '@/components/features/wiki/LazyWikiContent';
import ProjectWikiClient from '@/components/features/wiki/ProjectWikiClient';
import { Skeleton } from '@/components/ui/skeleton';

interface ProjectPageProps {
  params: Promise<{
    slug: string;
  }>;
  searchParams?: Promise<{ [key: string]: string | string[] | undefined }>;
}

// Generate static params for ISR
export async function generateStaticParams() {
  try {
    // Use direct fetch to avoid circular dependency and ensure proper caching
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/indexing-runs-with-wikis?limit=10`, {
      next: {
        revalidate: 1800, // 30 minutes cache
        tags: ['static-params']
      }
    });
    
    if (!response.ok) {
      console.warn('Failed to fetch projects for static generation:', response.status);
      return [];
    }
    
    const projects = await response.json();
    
    return projects.map((project: any) => {
      // Create slug format: wiki-for-[name]-[indexing_run_id]
      // Use indexing_run_id since that's what the frontend expects
      const projectName = project.wiki_structure?.title ? 
        project.wiki_structure.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') : 
        'project';
      return {
        slug: `wiki-for-${projectName}-${project.indexing_run_id}`,
      };
    });
  } catch (error) {
    console.error('Error generating static params:', error);
    // Return empty array to allow on-demand generation
    return [];
  }
}

// Allow dynamic params for projects not pre-built
export const dynamicParams = true;

// Generate metadata for SEO
export async function generateMetadata({ params }: ProjectPageProps) {
  try {
    const { slug } = await params;
    const project = await apiClient.getProjectFromSlug(slug);
    
    // Extract project name from slug since indexing runs don't have names
    const projectName = slug.replace(/-[a-f0-9-]{36}$/, '').replace(/-/g, ' ');
    const displayName = projectName.charAt(0).toUpperCase() + projectName.slice(1);
    
    return {
      title: `${displayName} - Wiki | ConstructionRAG`,
      description: `Explore the comprehensive wiki documentation for ${displayName}. Get insights into project requirements, specifications, and more.`,
      openGraph: {
        title: displayName,
        description: 'Project documentation and wiki',
        type: 'website',
      },
    };
  } catch (error) {
    return {
      title: 'Project Not Found',
      description: 'The requested project could not be found.',
    };
  }
}

async function ProjectWikiContent({ slug }: { slug: string }) {
  try {
    // Get project details (indexing run)
    const project = await apiClient.getProjectFromSlug(slug);
    
    // Get wiki runs for this indexing run
    const wikiRuns = await apiClient.getWikiRunsByIndexingRun(project.id);
    
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
    
    const firstPage = sortedPages[0];
    
    // Get content for the first page (serves as overview)
    const firstPageContent = await apiClient.getWikiPageContent(completedWikiRun.id, firstPage.name);

    return (
      <WikiLayout 
        pages={sortedPages}
        projectSlug={slug}
        content={firstPageContent.content}
        currentPage={firstPage.name}
      >
        <LazyWikiContent content={firstPageContent} />
      </WikiLayout>
    );
  } catch (error) {
    console.error('Error loading project wiki:', error);
    notFound();
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

export default async function ProjectPage({ params, searchParams }: ProjectPageProps) {
  const { slug } = await params;
  // Safe searchParams access - handle case where they're not available during static generation
  const search = searchParams ? await searchParams : {};
  const isClientNavigation = search?.client === 'true';
  
  // Use client-side progressive loading for in-app navigation
  if (isClientNavigation) {
    return <ProjectWikiClient slug={slug} />;
  }
  
  // Use server-side rendering for SEO/direct visits
  return (
    <Suspense fallback={<WikiLoadingSkeleton />}>
      <ProjectWikiContent slug={slug} />
    </Suspense>
  );
}

// Enable ISR without automatic revalidation
export const revalidate = 3600; // Revalidate every hour