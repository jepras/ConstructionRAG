'use client';

import { useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { useWikiTitle } from '@/components/providers/WikiTitleProvider';

interface WikiTitleFetcherProps {
  indexingRunId: string;
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

export default function WikiTitleFetcher({ indexingRunId }: WikiTitleFetcherProps) {
  const { setWikiTitle } = useWikiTitle();

  useEffect(() => {
    async function fetchTitle() {
      if (!indexingRunId) return;
      
      try {
        // Extract the actual UUID from the slug
        const actualRunId = extractUUIDFromSlug(indexingRunId);
        
        // Get wiki runs for this indexing run
        const wikiRuns = await apiClient.getWikiRunsByIndexingRun(actualRunId);
        
        // Find the first completed wiki run
        const completedWikiRun = wikiRuns.find(run => run.status === 'completed');
        
        if (!completedWikiRun) {
          // No wiki available, use a default title
          setWikiTitle('Project');
          return;
        }

        // Get wiki metadata to extract the title
        try {
          const wikiMetadata = await apiClient.getWikiMetadata(completedWikiRun.id);
          if (wikiMetadata?.metadata?.wiki_structure?.title) {
            setWikiTitle(wikiMetadata.metadata.wiki_structure.title);
          } else {
            setWikiTitle('Project');
          }
        } catch (error) {
          console.log('Could not fetch wiki metadata, using default title');
          setWikiTitle('Project');
        }
      } catch (error) {
        console.error('Error fetching wiki title:', error);
        setWikiTitle('Project');
      }
    }

    fetchTitle();
  }, [indexingRunId, setWikiTitle]);

  return null;
}