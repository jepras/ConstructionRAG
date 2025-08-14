'use client';

import { ReactNode } from 'react';
import WikiNavigation from './WikiNavigation';
import WikiTOC from './WikiTOC';
import { WikiPage } from '@/lib/api-client';

interface WikiLayoutProps {
  children: ReactNode;
  pages: WikiPage[];
  projectSlug: string;
  content?: string; // For TOC generation
  currentPage?: string;
}

export default function WikiLayout({ 
  children, 
  pages, 
  projectSlug, 
  content = '',
  currentPage 
}: WikiLayoutProps) {
  return (
    <div className="flex h-full rounded-lg relative">
      {/* Left sidebar - Navigation (sticky) */}
      <div className="hidden lg:flex sticky top-0 h-screen">
        <WikiNavigation 
          pages={pages} 
          projectSlug={projectSlug}
          currentPage={currentPage}
        />
        <div className="w-px bg-border"></div>
      </div>

      {/* Main content area (scrollable) */}
      <div className="flex-1 min-w-0 bg-card overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {children}
        </div>
      </div>

      {/* Right sidebar - Table of Contents (sticky) */}
      {content && (
        <div className="hidden xl:flex sticky top-0 h-screen">
          <div className="w-px bg-border"></div>
          <WikiTOC content={content} />
        </div>
      )}

      {/* Mobile navigation overlay - TODO: Implement mobile menu */}
      {/* This would show on mobile when menu button is tapped */}
    </div>
  );
}