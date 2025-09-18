'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChecklistResult } from '@/lib/api-client';

interface ResultsTableProps {
  results: ChecklistResult[];
}

const STATUS_CONFIG = {
  pending_clarification: {
    label: 'Pending Clarification',
    variant: 'secondary' as const,
    priority: 1
  },
  conditions: {
    label: 'Conditions',
    variant: 'outline' as const,
    priority: 2
  },
  risk: {
    label: 'Risk',
    variant: 'destructive' as const,
    priority: 3
  },
  missing: {
    label: 'Missing',
    variant: 'destructive' as const,
    priority: 4
  },
  found: {
    label: 'Found',
    variant: 'default' as const,
    priority: 5
  }
};

export default function ResultsTable({ results }: ResultsTableProps) {
  // Sort results by status priority (clarification → conditions → risk → missing → found)
  const sortedResults = [...results].sort((a, b) => {
    return STATUS_CONFIG[a.status].priority - STATUS_CONFIG[b.status].priority;
  });

  // Group results by status for better organization
  const groupedResults = sortedResults.reduce((acc, result) => {
    const status = result.status;
    if (!acc[status]) {
      acc[status] = [];
    }
    acc[status].push(result);
    return acc;
  }, {} as Record<ChecklistResult['status'], ChecklistResult[]>);

  return (
    <div className="space-y-6">
      <div className="bg-secondary/50 border border-border rounded-lg p-4">
        <h3 className="text-sm font-medium text-foreground mb-4">Analysis Results Summary</h3>
        
        {Object.entries(STATUS_CONFIG).map(([status, config]) => {
          const statusResults = groupedResults[status as ChecklistResult['status']] || [];
          
          if (statusResults.length === 0) return null;
          
          return (
            <div key={status} className="mb-6 last:mb-0">
              <div className="flex items-center gap-2 mb-3">
                <Badge variant={config.variant} className="text-xs">
                  {config.label}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  ({statusResults.length} items)
                </span>
              </div>
              
              <div className="bg-background border border-border rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <tbody>
                      {statusResults.map((result, index) => (
                        <tr key={result.id} className={index !== statusResults.length - 1 ? "border-b border-border" : ""}>
                          <td className="p-3 text-sm text-foreground font-mono">{result.item_number}</td>
                          <td className="p-3 text-sm text-foreground font-medium">{result.item_name}</td>
                          <td className="p-3 text-sm text-foreground">{result.description}</td>
                          <td className="p-3 text-sm text-muted-foreground">
                            <SourceCitation result={result} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          );
        })}
        
        {sortedResults.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No analysis results available. Please run an analysis first.
          </div>
        )}
      </div>
    </div>
  );
}

// Smart source citation component with multi-source support
function SourceCitation({ result }: { result: ChecklistResult }) {
  const [showAllSources, setShowAllSources] = React.useState(false);

  // Helper function to group sources by document
  const groupSourcesByDocument = (sources: typeof result.all_sources) => {
    if (!sources || sources.length === 0) return {};
    
    const grouped = sources.reduce((acc, source) => {
      const docKey = source.document;
      if (!acc[docKey]) {
        acc[docKey] = [];
      }
      acc[docKey].push(source);
      return acc;
    }, {} as Record<string, typeof sources>);
    
    return grouped;
  };

  // Primary source (fallback to single source fields if all_sources not available)
  const primarySource = result.all_sources?.[0] || 
    (result.source_document ? {
      document: result.source_document,
      page: result.source_page || 0,
      excerpt: result.source_excerpt
    } : null);

  const hasMultipleSources = result.all_sources && result.all_sources.length > 1;

  if (!primarySource) {
    return <span className="italic">Not specified</span>;
  }

  if (!hasMultipleSources) {
    // Single source - simple display
    return (
      <div className="space-y-1">
        <div>
          {primarySource.document} (p. {primarySource.page})
        </div>
        {primarySource.excerpt && (
          <div className="text-xs text-muted-foreground italic">
            "{primarySource.excerpt}"
          </div>
        )}
      </div>
    );
  }

  // Multiple sources - smart grouping and expandable display
  const groupedSources = groupSourcesByDocument(result.all_sources!);
  const documentNames = Object.keys(groupedSources);

  if (!showAllSources) {
    // Show condensed view
    return (
      <div className="space-y-1">
        <div>
          {primarySource.document} (p. {primarySource.page})
        </div>
        {primarySource.excerpt && (
          <div className="text-xs text-muted-foreground italic">
            "{primarySource.excerpt}"
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="h-auto p-0 text-xs text-primary hover:text-primary/80"
          onClick={() => setShowAllSources(true)}
        >
          Show all {result.all_sources!.length} sources
        </Button>
      </div>
    );
  }

  // Expanded view - show all sources grouped by document
  return (
    <div className="space-y-2">
      {documentNames.map((docName) => {
        const docSources = groupedSources[docName];
        const pages = docSources.map(s => s.page).filter(p => p > 0);
        const uniquePages = [...new Set(pages)].sort((a, b) => a - b);
        
        return (
          <div key={docName} className="space-y-1">
            <div>
              {docName} (p. {uniquePages.length > 3 
                ? `${uniquePages.slice(0, 3).join(', ')}, +${uniquePages.length - 3} more`
                : uniquePages.join(', ')
              })
            </div>
            {docSources[0].excerpt && (
              <div className="text-xs text-muted-foreground italic">
                "{docSources[0].excerpt}"
              </div>
            )}
          </div>
        );
      })}
      <Button
        variant="ghost"
        size="sm"
        className="h-auto p-0 text-xs text-primary hover:text-primary/80"
        onClick={() => setShowAllSources(false)}
      >
        Show less
      </Button>
    </div>
  );
}