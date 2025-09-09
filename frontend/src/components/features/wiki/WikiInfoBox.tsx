'use client';

import Link from 'next/link';
import { X } from 'lucide-react';
import { useState, useEffect } from 'react';

interface WikiInfoBoxProps {
  projectSlug: string;
}

const STORAGE_KEY = 'wiki-info-box-dismissed';

export default function WikiInfoBox({ projectSlug }: WikiInfoBoxProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check localStorage on mount
    const isDismissed = localStorage.getItem(STORAGE_KEY);
    if (!isDismissed) {
      setIsVisible(true);
    }
  }, []);

  const handleClose = () => {
    setIsVisible(false);
    // Store dismissal in localStorage
    localStorage.setItem(STORAGE_KEY, 'true');
  };

  if (!isVisible) {
    return null;
  }

  // Build the correct Q&A URL based on the project slug
  const queryUrl = projectSlug.includes('/dashboard')
    ? `/dashboard/projects/${projectSlug}/query`
    : `/projects/${projectSlug}/query`;

  return (
    <div className="mb-6 p-4 rounded-lg border border-primary/20 bg-primary/5 relative">
      <button
        onClick={handleClose}
        className="absolute top-3 right-3 text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Close info box"
      >
        <X className="h-4 w-4" />
      </button>
      <div className="space-y-2 pr-6">
        <p className="text-sm text-muted-foreground leading-relaxed">
          This is an automatically created overview based on the uploaded PDFs.
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed">
          You can ask questions to the document <Link 
            href={queryUrl}
            className="text-primary hover:text-primary/80 underline transition-colors"
          >here</Link>
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed">
          To generate overviews that automatically pulls the details you need from new projects, <Link 
            href="/pricing"
            className="text-primary hover:text-primary/80 underline transition-colors"
          >you need to create a user</Link>.
        </p>
      </div>
    </div>
  );
}