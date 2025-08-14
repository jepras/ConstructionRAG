'use client';

import { useEffect, useState } from 'react';
import AddProjectCard from './AddProjectCard';
import ProjectCard, { Project } from './ProjectCard';
import { apiClient } from '@/lib/api-client';
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

// Mock data for development
const mockProjects: Project[] = [
  {
    id: '1',
    name: 'Meridian Heights Development',
    description: 'A 42-story mixed-use development with residential and commercial spaces in downtown area.',
    stats: {
      documents: 5,
      wikiPages: 28,
      totalSize: '1.2 GB'
    },
    slug: 'meridian-heights-development-1'
  },
  {
    id: '2',
    name: 'City General Hospital Wing',
    description: 'Expansion project adding a new patient care wing and emergency department facilities.',
    stats: {
      documents: 12,
      wikiPages: 75,
      totalSize: '2.4 GB'
    },
    slug: 'city-general-hospital-wing-2'
  },
  {
    id: '3',
    name: 'Northwater Bridge Replacement',
    description: 'Seismic retrofit and replacement of a major transportation corridor bridge.',
    stats: {
      documents: 8,
      wikiPages: 41,
      totalSize: '980 MB'
    },
    slug: 'northwater-bridge-replacement-3'
  },
  {
    id: '4',
    name: 'Suburban Mall Extension',
    description: 'Addition of a new 50,000 sq. ft. two-story extension and food court.',
    stats: {
      documents: 3,
      wikiPages: 15,
      totalSize: '450 MB'
    },
    slug: 'suburban-mall-extension-4'
  },
  {
    id: '5',
    name: 'Heerup Skole Sikring',
    description: 'Security and access control system upgrade for an educational facility.',
    stats: {
      documents: 2,
      wikiPages: 9,
      totalSize: '180 MB'
    },
    slug: 'heerup-skole-sikring-5'
  },
  {
    id: '6',
    name: 'Downtown Tower Renovation',
    description: 'Complete facade and MEP systems overhaul for a 30-year-old high-rise.',
    stats: {
      documents: 21,
      wikiPages: 110,
      totalSize: '3.1 GB'
    },
    slug: 'downtown-tower-renovation-6'
  },
  {
    id: '7',
    name: 'Metro Line 3 Tunneling',
    description: 'Geotechnical and structural plans for a new underground transit line.',
    stats: {
      documents: 15,
      wikiPages: 55,
      totalSize: '1.9 GB'
    },
    slug: 'metro-line-3-tunneling-7'
  }
];

export default function ProjectGrid() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProjects() {
      try {
        console.log('🔍 Fetching public projects with wikis...');
        
        // Fetch completed wiki generations with their indexing run data
        const wikiRuns = await apiClient.getPublicProjectsWithWikis(5);
        console.log('📦 Wiki runs with indexing data:', wikiRuns);
        
        if (!wikiRuns || wikiRuns.length === 0) {
          console.log('⚠️ No completed wiki runs found, using mock data');
          setProjects(mockProjects.slice(0, 5));
          return;
        }

        // Transform wiki runs to project format
        const transformedProjects: Project[] = wikiRuns.map((wikiRun, index) => {
          console.log(`🔄 Processing wiki run ${index + 1}:`, wikiRun);
          
          const wikiStructure = wikiRun.wiki_structure || {};
          const pagesMetadata = wikiRun.pages_metadata || [];

          return {
            id: wikiRun.id, // Use wiki run ID instead of indexing_run_id to ensure uniqueness
            name: wikiStructure.title || `Project ${index + 1}`,
            description: wikiStructure.description || 'Construction project documentation',
            stats: {
              documents: 1, // Assume at least 1 document if wiki was generated
              wikiPages: pagesMetadata.length || 0,
              totalSize: formatFileSize(getTotalSize(pagesMetadata))
            },
            slug: `${(wikiStructure.title || `project-${index + 1}`).toLowerCase().replace(/\s+/g, '-')}-${wikiRun.indexing_run_id}`
          };
        });

        console.log('✅ Transformed projects:', transformedProjects);
        setProjects(transformedProjects);
      } catch (err) {
        console.error('❌ Failed to fetch projects:', err);
        console.log('📋 Using mock data as fallback');
        setProjects(mockProjects.slice(0, 5));
        // Don't show error to user if we have fallback data
        // setError('Failed to load projects. Please try again later.');
      } finally {
        setLoading(false);
      }
    }

    fetchProjects();
  }, []);

  if (loading) {
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
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">{error}</p>
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