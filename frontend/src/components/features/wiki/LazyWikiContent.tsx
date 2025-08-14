'use client';

import dynamic from 'next/dynamic';
import { WikiPageContent } from '@/lib/api-client';
import { Skeleton } from '@/components/ui/skeleton';

// Dynamically import WikiContent with all its heavy dependencies
const WikiContent = dynamic(
  () => import('./WikiContent'),
  {
    loading: () => (
      <div className="max-w-none">
        {/* Header skeleton */}
        <div className="mb-8">
          <Skeleton className="h-10 w-3/4 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
        
        {/* Content skeleton */}
        <div className="space-y-4">
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-5/6" />
          <Skeleton className="h-6 w-4/5" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <Skeleton className="h-32 w-full" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </div>
      </div>
    ),
    ssr: false, // Disable SSR to ensure client-side only loading
  }
);

interface LazyWikiContentProps {
  content: WikiPageContent;
}

export default function LazyWikiContent({ content }: LazyWikiContentProps) {
  return <WikiContent content={content} />;
}