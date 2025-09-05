'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { BookOpen, MessageSquare, Settings, Database, Share2, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { apiClient } from '@/lib/api-client';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

// Helper function to determine the base path based on current context
function getBasePath(pathname: string): string {
  return pathname.startsWith('/dashboard') ? '/dashboard/projects' : '/projects';
}

interface ProjectHeaderProps {
  projectSlug: string;
  projectName: string;
  runId?: string;
}

const navigationTabs = [
  {
    name: 'Wiki',
    href: '',
    icon: BookOpen,
    description: 'Project documentation and wiki pages'
  },
  {
    name: 'Q&A',
    href: '/query',
    icon: MessageSquare,
    description: 'Ask questions about the project'
  },
  {
    name: 'Index',
    href: '/indexing',
    icon: Database,
    description: 'Indexing progress and details'
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Project settings and configuration'
  }
];

// Extract project ID from projectSlug format: "project-name-{project_id}"
function extractProjectIdFromSlug(projectSlug: string): string | null {
  const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const match = projectSlug.match(uuidRegex);
  return match ? match[0] : null;
}

export default function ProjectHeader({ projectSlug, projectName, runId }: ProjectHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  
  // Determine base path based on current context
  const basePath = getBasePath(pathname);
  
  // Check if this is a public project (single-slug format without nested structure)
  const isPublicProject = basePath === '/projects' && !projectSlug.includes('/');
  
  // Handle nested vs single slug format
  const [extractedProjectSlug, extractedRunId] = projectSlug.includes('/') 
    ? projectSlug.split('/')
    : [projectSlug, runId];
    
  const baseProjectPath = isPublicProject 
    ? `${basePath}/${extractedProjectSlug}` 
    : `${basePath}/${extractedProjectSlug}/${extractedRunId}`;
  
  // Extract project ID from the slug (only for private projects)
  const projectId = !isPublicProject ? extractProjectIdFromSlug(extractedProjectSlug) : null;
  
  // Fetch available runs for version dropdown (only for private projects)
  const { data: projectRuns = [], isLoading } = useQuery({
    queryKey: ['project-runs', projectId],
    queryFn: () => projectId ? apiClient.getProjectRuns(projectId) : Promise.resolve([]),
    enabled: !!projectId && !isPublicProject, // Only fetch for private projects
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handleVersionChange = (newRunId: string) => {
    // Navigate to the same tab but with different run ID
    const currentPath = pathname.replace(`${basePath}/${extractedProjectSlug}/${extractedRunId}`, '');
    const newPath = `${basePath}/${extractedProjectSlug}/${newRunId}${currentPath}`;
    router.push(newPath);
  };

  const handleShare = async () => {
    try {
      // Get the current page URL
      const currentUrl = window.location.href;
      
      // Copy to clipboard
      await navigator.clipboard.writeText(currentUrl);
      
      // Show success toast
      toast.success("URL copied to clipboard!");
    } catch (error) {
      // Fallback for browsers that don't support clipboard API
      console.error('Failed to copy to clipboard:', error);
      toast.error("Failed to copy URL. Please copy manually from the address bar.");
    }
  };

  // Find current run info
  const currentRun = projectRuns.find(run => run.id === extractedRunId);
  const currentRunName = currentRun ? `Run ${currentRun.id.slice(0, 8)}` : 'Current Version';

  return (
    <div className="bg-background">
      <div className="container mx-auto px-4">
        {/* Project title */}
        <div className="py-6 text-center">
          <h1 className="text-3xl font-bold text-white">{projectName}</h1>
        </div>

        {/* Navigation tabs with controls */}
        <div className="flex items-center justify-between border-b border-border">
          <nav className="flex space-x-8" role="tablist">
            {navigationTabs.map((tab) => {
              const href = `${baseProjectPath}${tab.href}`;
              
              // Special logic for Wiki tab - it should be active for all wiki pages
              const isActive = tab.name === 'Wiki' 
                ? (pathname === href || pathname.startsWith(`${href}/`))
                : pathname === href;
                
              const Icon = tab.icon;

              return (
                <Link
                  key={tab.name}
                  href={href}
                  className={cn(
                    "inline-flex items-center gap-2 px-1 py-4 text-sm font-medium border-b-2 transition-colors",
                    isActive
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                  )}
                  role="tab"
                  aria-selected={isActive}
                  title={tab.description}
                >
                  <Icon className="w-4 h-4" />
                  {tab.name}
                </Link>
              );
            })}
          </nav>

          {/* Controls */}
          <div className="flex items-center gap-3 pb-2">
            {/* Version/Indexing Run Dropdown - Only show for private projects */}
            {!isPublicProject && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="flex items-center gap-2">
                    <span className="text-sm">{currentRunName}</span>
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  {isLoading ? (
                    <DropdownMenuItem disabled>
                      <span className="text-sm text-muted-foreground">Loading versions...</span>
                    </DropdownMenuItem>
                  ) : projectRuns.length > 0 ? (
                    projectRuns.map((run) => (
                      <DropdownMenuItem 
                        key={run.id}
                        onClick={() => handleVersionChange(run.id)}
                        className={cn(
                          "flex flex-col items-start space-y-1 cursor-pointer",
                          run.id === extractedRunId && "bg-accent"
                        )}
                      >
                        <span className="font-medium">Run {run.id.slice(0, 8)}</span>
                        <span className="text-xs text-muted-foreground">
                          {run.status} • {new Date(run.created_at).toLocaleDateString()}
                        </span>
                      </DropdownMenuItem>
                    ))
                  ) : (
                    <DropdownMenuItem disabled>
                      <span className="text-sm text-muted-foreground">No other versions available</span>
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {/* Public Project Badge - Show for public projects instead of version dropdown */}
            {isPublicProject && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 border border-border rounded-md">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span className="text-sm text-muted-foreground">Public Project</span>
              </div>
            )}

            {/* Share Button */}
            <Button size="sm" className="flex items-center gap-2" onClick={handleShare}>
              <Share2 className="w-4 h-4" />
              <span>Share</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}