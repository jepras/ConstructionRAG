'use client';

import Link from 'next/link';
import { FileText, BookOpen, HardDrive, ArrowRight } from 'lucide-react';

export interface ProjectStats {
  documents: number;
  wikiPages: number;
  totalSize: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  stats: ProjectStats;
  slug: string;
}

interface ProjectCardProps {
  project: Project;
}

export default function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link 
      href={`/projects/${project.slug}`}
      className="group relative flex flex-col p-6 rounded-lg border border-border bg-card hover:bg-accent/5 hover:border-primary/20 transition-all duration-200 min-h-[200px]"
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
          <div className="flex items-center gap-1">
            <FileText className="w-3.5 h-3.5" />
            <span>{project.stats.documents}</span>
          </div>
          <div className="flex items-center gap-1">
            <BookOpen className="w-3.5 h-3.5" />
            <span>{project.stats.wikiPages}</span>
          </div>
          <div className="flex items-center gap-1">
            <HardDrive className="w-3.5 h-3.5" />
            <span>{project.stats.totalSize}</span>
          </div>
        </div>
        
        <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
      </div>
    </Link>
  );
}