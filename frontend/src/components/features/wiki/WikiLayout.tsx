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
    <div className="flex min-h-screen bg-background">
      {/* Left sidebar - Navigation */}
      <div className="hidden lg:block">
        <WikiNavigation 
          pages={pages} 
          projectSlug={projectSlug}
          currentPage={currentPage}
        />
      </div>

      {/* Main content area */}
      <div className="flex-1 min-w-0">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {children}
        </div>
      </div>

      {/* Right sidebar - Table of Contents */}
      {content && (
        <div className="hidden xl:block">
          <WikiTOC content={content} />
        </div>
      )}

      {/* Mobile navigation overlay - TODO: Implement mobile menu */}
      {/* This would show on mobile when menu button is tapped */}
    </div>
  );
}