'use client';

import { useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { useWikiTitle } from '@/components/providers/WikiTitleProvider';

interface WikiTitleFetcherProps {
  indexingRunId: string;
  initialTitle?: string; // Optional title to set immediately without API call
}

// Extract UUID from slug format: "project-name-{uuid}"
function extractUUIDFromSlug(slug: string): string {
  const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const match = slug.match(uuidRegex);
  if (!match) {
    throw new Error(`Invalid slug format, no UUID found: ${slug}`);
  }
  return match[0];
}

export default function WikiTitleFetcher({ indexingRunId, initialTitle }: WikiTitleFetcherProps) {
  const { setWikiTitle } = useWikiTitle();

  useEffect(() => {
    // If we have an initial title, use it immediately
    if (initialTitle) {
      setWikiTitle(initialTitle);
      return;
    }

    // Otherwise, fetch the title via API (fallback for backward compatibility)
    async function fetchTitle() {
      if (!indexingRunId) return;
      
      try {
        // Extract the actual UUID from the slug
        const actualRunId = extractUUIDFromSlug(indexingRunId);
        
        // Use the new batched endpoint for better performance
        const wikiData = await apiClient.getWikiInitialData(actualRunId);
        
        if (wikiData.metadata?.metadata?.wiki_structure?.title) {
          setWikiTitle(wikiData.metadata.metadata.wiki_structure.title);
        } else {
          setWikiTitle('Project');
        }
      } catch (error) {
        console.error('Error fetching wiki title:', error);
        setWikiTitle('Project');
      }
    }

    fetchTitle();
  }, [indexingRunId, initialTitle, setWikiTitle]);

  return null;
}