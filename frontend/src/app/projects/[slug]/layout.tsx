'use client';

import React, { ReactNode } from 'react';
import { Header } from '@/components/layout/Header';
import ProjectHeader from '@/components/layout/ProjectHeader';
import { useAuth } from '@/components/providers/AuthProvider';

interface ProjectLayoutProps {
  children: ReactNode;
  params: Promise<{
    slug: string;
  }>;
}

export default function ProjectLayout({ children, params }: ProjectLayoutProps) {
  const { isAuthenticated } = useAuth();
  
  // Handle params properly in client component
  const [slug, setSlug] = React.useState<string>('');
  
  React.useEffect(() => {
    params.then(({ slug }) => setSlug(slug));
  }, [params]);
  
  // Extract project name from slug (everything before the UUID)
  const uuidRegex = /-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const projectName = slug.replace(uuidRegex, '').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div className="min-h-screen bg-background">
      <Header variant={isAuthenticated ? "app" : "marketing"} />
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