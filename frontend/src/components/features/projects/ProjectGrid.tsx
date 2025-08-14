'use client';

import AddProjectCard from './AddProjectCard';
import ProjectCard, { Project } from './ProjectCard';
import { usePublicProjectsWithWikis } from '@/hooks/useApiQueries';
import { Skeleton } from '@/components/ui/skeleton';

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
  const { data: wikiRuns, isLoading, error } = usePublicProjectsWithWikis(5);

  // Transform wiki runs to project format
  const projects: Project[] = wikiRuns && wikiRuns.length > 0 
    ? wikiRuns.map((wikiRun, index) => {
        console.log(`🔄 Processing wiki run ${index + 1}:`, wikiRun);
        
        const wikiStructure = wikiRun.wiki_structure || {};
        const pagesMetadata = wikiRun.pages_metadata || [];
        
        console.log(`📝 Wiki structure title: "${wikiStructure.title || 'NOT FOUND'}"`);
        console.log(`📄 Pages metadata count: ${pagesMetadata.length}`);

        return {
          id: wikiRun.id, // Use wiki run ID instead of indexing_run_id to ensure uniqueness
          name: wikiStructure.title || 'Name not found',
          description: wikiStructure.description || 'Construction project documentation',
          stats: {
            documents: 1, // Assume at least 1 document if wiki was generated
            wikiPages: pagesMetadata.length || 0,
            totalSize: formatFileSize(getTotalSize(pagesMetadata))
          },
          slug: `${(wikiStructure.title || 'name-not-found').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')}-${wikiRun.indexing_run_id}`
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

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <AddProjectCard />
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}