'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, MessageSquare, Settings, Database, Share2, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ProjectHeaderProps {
  projectSlug: string;
  projectName: string;
}

const navigationTabs = [
  {
    name: 'Wiki',
    href: '',
    icon: BookOpen,
    description: 'Project documentation and wiki pages'
  },
  {
    name: 'Q&A',
    href: '/query',
    icon: MessageSquare,
    description: 'Ask questions about the project'
  },
  {
    name: 'Index',
    href: '/indexing',
    icon: Database,
    description: 'Indexing progress and details'
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Project settings and configuration'
  }
];

export default function ProjectHeader({ projectSlug, projectName }: ProjectHeaderProps) {
  const pathname = usePathname();
  const baseProjectPath = `/projects/${projectSlug}`;

  return (
    <div className="bg-background">
      <div className="container mx-auto px-4">
        {/* Project title */}
        <div className="py-6">
          <h1 className="text-3xl font-bold text-foreground mb-2">{projectName}</h1>
          <p className="text-muted-foreground">
            Explore project documentation, ask questions, and manage settings
          </p>
        </div>

        {/* Navigation tabs with controls */}
        <div className="flex items-center justify-between border-b border-border">
          <nav className="flex space-x-8" role="tablist">
            {navigationTabs.map((tab) => {
              const href = `${baseProjectPath}${tab.href}`;
              const isActive = pathname === href;
              const Icon = tab.icon;

              return (
                <Link
                  key={tab.name}
                  href={href}
                  className={cn(
                    "inline-flex items-center gap-2 px-1 py-4 text-sm font-medium border-b-2 transition-colors",
                    isActive
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                  )}
                  role="tab"
                  aria-selected={isActive}
                  title={tab.description}
                >
                  <Icon className="w-4 h-4" />
                  {tab.name}
                </Link>
              );
            })}
          </nav>

          {/* Controls */}
          <div className="flex items-center gap-3 pb-2">
            {/* Version/Indexing Run Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="flex items-center gap-2">
                  <span className="text-sm">Kapacitetsudvidelse</span>
                  <ChevronDown className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem>
                  <div className="flex flex-col">
                    <span className="font-medium">Kapacitetsudvidelse</span>
                    <span className="text-xs text-muted-foreground">Current version</span>
                  </div>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Share Button */}
            <Button size="sm" className="flex items-center gap-2">
              <Share2 className="w-4 h-4" />
              <span>Share</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}