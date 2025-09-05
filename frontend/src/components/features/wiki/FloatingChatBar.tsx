'use client';

import { useState, KeyboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FloatingChatBarProps {
  projectSlug: string;
  isAuthenticated?: boolean;
}

export default function FloatingChatBar({ projectSlug, isAuthenticated = false }: FloatingChatBarProps) {
  const [query, setQuery] = useState('');
  const router = useRouter();

  const handleSubmit = () => {
    if (!query.trim()) return;

    // Construct the appropriate query URL based on authentication status
    let queryUrl: string;
    
    if (isAuthenticated) {
      // Authenticated projects use nested format: /dashboard/projects/{projectSlug}/{runId}/query
      queryUrl = `/dashboard/projects/${projectSlug}/query?q=${encodeURIComponent(query.trim())}`;
    } else {
      // Public projects use single slug format: /projects/{indexingRunId}/query
      queryUrl = `/projects/${projectSlug}/query?q=${encodeURIComponent(query.trim())}`;
    }

    // Open in new tab
    window.open(queryUrl, '_blank');
    
    // Clear the input after submitting
    setQuery('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4">
      <div className="max-w-2xl mx-auto">
        <div className={cn(
          "bg-primary/5 backdrop-blur-lg rounded-2xl shadow-2xl border border-primary/20",
          "transition-all duration-200"
        )}>
          <div className="flex items-center gap-3 p-2">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Ask anything about the project..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                className={cn(
                  "w-full bg-transparent text-base py-2 px-0",
                  "border-0 outline-none focus:outline-none",
                  "placeholder:text-muted-foreground/70 text-foreground",
                  "appearance-none"
                )}
                style={{ background: 'transparent' }}
              />
            </div>
            <Button
              onClick={handleSubmit}
              disabled={!query.trim()}
              size="sm"
              className={cn(
                "rounded-full transition-all duration-200",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                "hover:scale-105 active:scale-95"
              )}
            >
              <Send className="size-4" />
              <span className="sr-only">Send query</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}