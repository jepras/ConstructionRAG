'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, MessageSquare, Settings, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

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
    <div className="border-b border-border bg-background">
      <div className="container mx-auto px-4">
        {/* Project title */}
        <div className="py-6">
          <h1 className="text-3xl font-bold text-foreground mb-2">{projectName}</h1>
          <p className="text-muted-foreground">
            Explore project documentation, ask questions, and manage settings
          </p>
        </div>

        {/* Navigation tabs */}
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
      </div>
    </div>
  );
}