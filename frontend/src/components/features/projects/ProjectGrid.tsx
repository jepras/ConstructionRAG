'use client';

import AddProjectCard from './AddProjectCard';
import ProjectCard, { Project } from './ProjectCard';
import { usePublicProjectsWithWikis } from '@/hooks/useApiQueries';
import { Skeleton } from '@/components/ui/skeleton';
import { useSearchParams } from 'next/navigation';
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';

// Helper functions
function getTotalSize(pagesMetadata: any[]): number {
  return pagesMetadata.reduce((total, page) => total + (page.file_size || 0), 0);
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / Math.pow(k, i)) * 10) / 10} ${sizes[i]}`;
}

// Mock data removed - using real API data only

export default function ProjectGrid() {
  const searchParams = useSearchParams();
  const currentPageParam = searchParams.get('page');
  const currentPage = Math.max(parseInt(currentPageParam || '1', 10) || 1, 1);

  // Fetch a generous amount and paginate client-side
  const { data: wikiRuns, isLoading, error } = usePublicProjectsWithWikis(50);

  // Transform wiki runs to project format
  const projects: Project[] = wikiRuns && wikiRuns.length > 0
    ? wikiRuns.map((wikiRun, index) => {
      const wikiStructure = wikiRun.wiki_structure || {};
      const pagesMetadata = wikiRun.pages_metadata || [];

      // Extract unified project info from API response
      const projects = wikiRun.projects || {};
      const username = projects.username || 'anonymous';
      const projectSlug = projects.project_slug || 'unknown-project';

      return {
        id: wikiRun.id, // Use wiki run ID instead of indexing_run_id to ensure uniqueness
        name: wikiStructure.title || 'Name not found',
        description: wikiStructure.description || 'Construction project documentation',
        language: wikiRun.language || 'da', // Default to Danish if language not specified
        accessLevel: wikiRun.access_level || 'public',
        slug: `${username}/${projectSlug}` // Use unified GitHub-style URL structure
      };
    })
    : []; // No fallback - show empty state if no real data

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Skeleton className="h-[200px] rounded-lg" />
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} className="h-[200px] rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    console.error('❌ Failed to fetch projects:', error);
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">
          Unable to load projects at the moment.
        </p>
        <p className="text-sm text-muted-foreground">
          Please try again later.
        </p>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">
          No public projects with wikis available yet.
        </p>
        <p className="text-sm text-muted-foreground">
          Upload your first project to get started!
        </p>
      </div>
    );
  }

  const pageSize = 10;
  const totalPages = Math.max(Math.ceil(projects.length / pageSize), 1);
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const visible = projects.slice(startIndex, startIndex + pageSize);

  const getHref = (page: number) => `?page=${page}`;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <AddProjectCard />
        {visible.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="mt-8">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious href={getHref(Math.max(safeCurrentPage - 1, 1))} />
              </PaginationItem>

              {/* Render up to 5 number links with ellipsis */}
              {(() => {
                const items: React.ReactNode[] = [];
                const maxShown = 5;
                let start = Math.max(1, safeCurrentPage - 2);
                let end = Math.min(totalPages, start + maxShown - 1);
                if (end - start + 1 < maxShown) {
                  start = Math.max(1, end - maxShown + 1);
                }

                if (start > 1) {
                  items.push(
                    <PaginationItem key={1}>
                      <PaginationLink href={getHref(1)}>1</PaginationLink>
                    </PaginationItem>
                  );
                  if (start > 2) {
                    items.push(<PaginationEllipsis key="start-ellipsis" />);
                  }
                }

                for (let p = start; p <= end; p += 1) {
                  items.push(
                    <PaginationItem key={p}>
                      <PaginationLink href={getHref(p)} isActive={p === safeCurrentPage}>
                        {p}
                      </PaginationLink>
                    </PaginationItem>
                  );
                }

                if (end < totalPages) {
                  if (end < totalPages - 1) {
                    items.push(<PaginationEllipsis key="end-ellipsis" />);
                  }
                  items.push(
                    <PaginationItem key={totalPages}>
                      <PaginationLink href={getHref(totalPages)}>{totalPages}</PaginationLink>
                    </PaginationItem>
                  );
                }

                return items;
              })()}

              <PaginationItem>
                <PaginationNext href={getHref(Math.min(safeCurrentPage + 1, totalPages))} />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}
    </>
  );
}