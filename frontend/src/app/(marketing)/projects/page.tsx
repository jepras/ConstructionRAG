import { Suspense } from 'react';
import ProjectGrid from '@/components/features/projects/ProjectGrid';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = {
  title: "Projects",
};

export default function ProjectsPage() {
  return (
    <div className="container mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold text-foreground mb-8 text-center">
        Explore Public Projects
      </h1>
      
      <Suspense fallback={<ProjectGridSkeleton />}>
        <ProjectGrid />
      </Suspense>
    </div>
  );
}

function ProjectGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[...Array(7)].map((_, i) => (
        <div key={i} className="h-48">
          <Skeleton className="w-full h-full" />
        </div>
      ))}
    </div>
  );
}