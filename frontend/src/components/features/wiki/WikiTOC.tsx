'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface TOCItem {
  id: string;
  title: string;
  level: number;
}

interface WikiTOCProps {
  content: string;
}

// Extract headings from markdown content
function extractTOCFromMarkdown(markdown: string): TOCItem[] {
  const headingRegex = /^(#{1,6})\s+(.+)$/gm;
  const toc: TOCItem[] = [];
  let match;

  while ((match = headingRegex.exec(markdown)) !== null) {
    const level = match[1].length;
    const title = match[2].trim();
    const id = title
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s+/g, '-')
      .trim();

    toc.push({ id, title, level });
  }

  return toc;
}

// Scroll spy hook to track active section
function useActiveSection(tocItems: TOCItem[]) {
  const [activeId, setActiveId] = useState<string>('');

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visibleSections = entries
          .filter((entry) => entry.isIntersecting)
          .map((entry) => entry.target.id);

        if (visibleSections.length > 0) {
          setActiveId(visibleSections[0]);
        }
      },
      {
        rootMargin: '-20% 0% -35% 0%',
        threshold: 0.1,
      }
    );

    // Observe all heading elements
    tocItems.forEach(({ id }) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });

    return () => observer.disconnect();
  }, [tocItems]);

  return activeId;
}

export default function WikiTOC({ content }: WikiTOCProps) {
  const tocItems = extractTOCFromMarkdown(content);
  const activeId = useActiveSection(tocItems);

  if (tocItems.length === 0) {
    return null;
  }

  const handleClick = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  };

  return (
    <div className="w-64 bg-card h-full flex flex-col">
      <div className="p-4 flex-1 overflow-y-auto">
        <h3 className="text-sm font-semibold text-foreground mb-4 uppercase tracking-wide pt-6 sticky top-0 bg-card">
          On This Page
        </h3>

        <nav className="space-y-1">
          {tocItems.map((item) => (
            <button
              key={item.id}
              onClick={() => handleClick(item.id)}
              className={cn(
                "block w-full text-left text-sm py-1.5 px-2 rounded-sm transition-colors",
                "hover:text-foreground hover:bg-accent",
                item.level > 2 && "text-xs",
                activeId === item.id
                  ? "text-primary font-medium bg-primary/5 border-l-2 border-primary"
                  : "text-muted-foreground"
              )}
              style={{
                paddingLeft: `${0.5 + (item.level - 1) * 0.75}rem`,
              }}
            >
              <span className="line-clamp-2">{item.title}</span>
            </button>
          ))}
        </nav>

        {/* Scroll to top button */}
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="mt-6 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          ← Back to top
        </button>
      </div>
    </div>
  );
}