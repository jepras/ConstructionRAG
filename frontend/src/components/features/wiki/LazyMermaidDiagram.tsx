'use client';

import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';

// Dynamically import MermaidDiagram to avoid loading mermaid library unnecessarily
const MermaidDiagram = dynamic(
  () => import('./MermaidDiagram'),
  {
    loading: () => (
      <div className="my-6">
        <div className="flex justify-center items-center bg-background border border-border rounded-lg p-4">
          <div className="space-y-2 w-full max-w-md">
            <Skeleton className="h-4 w-3/4 mx-auto" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-4 w-1/2 mx-auto" />
          </div>
        </div>
      </div>
    ),
    ssr: false, // Client-side only to avoid SSR issues with mermaid
  }
);

interface LazyMermaidDiagramProps {
  children: string;
}

export default function LazyMermaidDiagram({ children }: LazyMermaidDiagramProps) {
  return <MermaidDiagram>{children}</MermaidDiagram>;
}