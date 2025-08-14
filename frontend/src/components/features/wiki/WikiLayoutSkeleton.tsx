'use client';

import WikiNavigation from './WikiNavigation';
import { Skeleton } from '@/components/ui/skeleton';
import { WikiPage } from '@/lib/api-client';

interface WikiLayoutSkeletonProps {
  pages: WikiPage[];
  projectSlug: string;
  currentPage?: string;
}

export default function WikiLayoutSkeleton({ 
  pages, 
  projectSlug, 
  currentPage 
}: WikiLayoutSkeletonProps) {
  return (
    <div className="flex h-full rounded-lg relative">
      {/* Left sidebar - Actual Navigation (stable) */}
      <div className="hidden lg:flex sticky top-0 h-screen">
        <WikiNavigation 
          pages={pages} 
          projectSlug={projectSlug}
          currentPage={currentPage}
        />
        <div className="w-px bg-border"></div>
      </div>

      {/* Main content area - Skeleton */}
      <div className="flex-1 min-w-0 bg-card overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <Skeleton className="h-10 w-3/4 mb-4" />
          <Skeleton className="h-4 w-1/2 mb-8" />
          <div className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        </div>
      </div>

      {/* Right sidebar - TOC Skeleton */}
      <div className="hidden xl:flex sticky top-0 h-screen">
        <div className="w-px bg-border"></div>
        <div className="w-64 bg-card h-full">
          <div className="p-4 space-y-2">
            <Skeleton className="h-5 w-24" />
            <div className="space-y-1">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-5/6" />
              <Skeleton className="h-6 w-4/5" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-3/4" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}