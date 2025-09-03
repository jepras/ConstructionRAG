'use client';

import dynamic from 'next/dynamic';
import { Loader2 } from 'lucide-react';

// Dynamically import PDF components with no SSR
const PDFPageViewer = dynamic(
  () => import('./PDFPageViewer'),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">Loading PDF viewer...</span>
        </div>
      </div>
    )
  }
);

const PDFFullViewer = dynamic(
  () => import('./PDFFullViewer'),
  { 
    ssr: false,
    loading: () => null
  }
);

export { PDFPageViewer, PDFFullViewer };