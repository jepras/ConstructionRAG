'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { ArrowRight, Loader2, Globe, Lock } from 'lucide-react';
import { usePrefetchProject } from '@/hooks/useApiQueries';

export interface Project {
  id: string;
  name: string;
  description: string;
  language: string;
  accessLevel: string;
  slug: string;
}

interface ProjectCardProps {
  project: Project;
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const router = useRouter();
  const prefetchProject = usePrefetchProject();
  const [isNavigating, setIsNavigating] = useState(false);

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    setIsNavigating(true);
    
    // Navigate to project page using unified GitHub-style URL structure
    router.push(`/${project.slug}`);
  };

  const handleMouseEnter = () => {
    // Prefetch project data on hover for instant navigation
    prefetchProject(project.slug);
  };

  return (
    <div 
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      className="group relative flex flex-col p-6 rounded-lg border border-border bg-card hover:bg-accent/5 hover:border-primary/20 transition-all duration-200 min-h-[200px] cursor-pointer"
    >
      <div className="flex-1">
        <h3 className="text-lg font-semibold text-foreground mb-2 line-clamp-1">
          {project.name}
        </h3>
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
          {project.description}
        </p>
      </div>
      
      <div className="flex items-center justify-between pt-4 border-t border-border/50">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {/* Language flags */}
          {(project.language === 'da' || project.language === 'danish') && (
            <div className="flex items-center gap-1">
              <span className="text-sm">🇩🇰</span>
              <span>Danish</span>
            </div>
          )}
          {(project.language === 'en' || project.language === 'english') && (
            <div className="flex items-center gap-1">
              <span className="text-sm">🇬🇧</span>
              <span>English</span>
            </div>
          )}
          
          {/* Access level indicator */}
          <div className="flex items-center gap-1">
            {project.accessLevel === 'public' ? (
              <>
                <Globe className="w-3.5 h-3.5" />
                <span>Public</span>
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5" />
                <span>Private</span>
              </>
            )}
          </div>
        </div>
        
        {isNavigating ? (
          <Loader2 className="w-4 h-4 text-primary animate-spin" />
        ) : (
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
        )}
      </div>
    </div>
  );
}