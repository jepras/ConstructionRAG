'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { WikiPage } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { ChevronRight, ChevronDown, FileText } from 'lucide-react';
import { useState } from 'react';

interface WikiNavigationProps {
  pages: WikiPage[];
  projectSlug: string;
  currentPage?: string;
}

interface NavigationItemProps {
  page: WikiPage;
  projectSlug: string;
  isActive: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}

function NavigationItem({ page, projectSlug, isActive, isExpanded, onToggle, isFirstPage }: NavigationItemProps & { isFirstPage: boolean }) {
  const hasSubsections = page.sections && page.sections.length > 0;
  
  // First page routes to base project URL, others to specific page URLs
  const pageUrl = isFirstPage ? `/projects/${projectSlug}` : `/projects/${projectSlug}/${page.name}`;
  
  return (
    <div className="mb-1">
      {/* Main page link */}
      <div className="flex items-center">
        <Link
          href={pageUrl}
          className={cn(
            "flex-1 flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors",
            isActive
              ? "bg-primary/10 text-primary font-medium"
              : "text-foreground hover:bg-accent hover:text-accent-foreground"
          )}
        >
          <FileText className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">{page.title}</span>
        </Link>
        
        {/* Expand/collapse button for pages with subsections */}
        {hasSubsections && (
          <button
            onClick={onToggle}
            className="p-1.5 text-muted-foreground hover:text-foreground transition-colors"
            aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${page.title} sections`}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Subsections */}
      {hasSubsections && isExpanded && (
        <div className="ml-6 mt-1 space-y-1">
          {page.sections?.map((section) => (
            <Link
              key={section.id}
              href={`${pageUrl}#${section.id}`}
              className="block px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded-sm hover:bg-accent"
            >
              <span className="flex items-center gap-1">
                <span className="text-xs opacity-50">{'─'.repeat(section.level - 1)}</span>
                {section.title}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WikiNavigation({ pages, projectSlug, currentPage }: WikiNavigationProps) {
  const pathname = usePathname();
  const [expandedPages, setExpandedPages] = useState<Set<string>>(new Set());

  const handleToggle = (pageName: string) => {
    setExpandedPages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(pageName)) {
        newSet.delete(pageName);
      } else {
        newSet.add(pageName);
      }
      return newSet;
    });
  };

  // Sort pages by order
  const sortedPages = [...pages].sort((a, b) => a.order - b.order);
  const firstPage = sortedPages[0];

  // Determine current active page from pathname or currentPage prop
  const activePageName = currentPage || (() => {
    if (pathname === `/projects/${projectSlug}`) {
      return firstPage?.name; // First page is active when on base URL
    }
    const segments = pathname.split('/');
    return segments[segments.length - 1];
  })();

  return (
    <div className="w-64 bg-background border-r border-border h-full">
      <div className="p-4">
        <h2 className="text-lg font-semibold text-foreground mb-4">
          Documentation
        </h2>
        
        <nav className="space-y-1">
          {sortedPages.map((page, index) => (
            <NavigationItem
              key={page.name}
              page={page}
              projectSlug={projectSlug}
              isActive={page.name === activePageName}
              isExpanded={expandedPages.has(page.name || '')}
              onToggle={() => handleToggle(page.name || '')}
              isFirstPage={index === 0}
            />
          ))}
        </nav>
        
        {pages.length === 0 && (
          <div className="text-sm text-muted-foreground py-4">
            No wiki pages available yet.
          </div>
        )}
      </div>
    </div>
  );
}