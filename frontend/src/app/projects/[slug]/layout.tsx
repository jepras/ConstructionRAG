import { ReactNode } from 'react';
import ProjectHeader from '@/components/layout/ProjectHeader';

interface ProjectLayoutProps {
  children: ReactNode;
  params: Promise<{
    slug: string;
  }>;
}

export default async function ProjectLayout({ children, params }: ProjectLayoutProps) {
  const { slug } = await params;
  
  // Extract project name from slug (everything before the UUID)
  const uuidRegex = /-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const projectName = slug.replace(uuidRegex, '').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div className="min-h-screen bg-background">
      <ProjectHeader 
        projectSlug={slug} 
        projectName={projectName || "Project"}
      />
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}