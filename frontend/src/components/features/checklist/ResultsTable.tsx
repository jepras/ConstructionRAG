'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';

export interface ChecklistResult {
  id: string;
  number: string;
  name: string;
  status: 'pending_clarification' | 'conditions' | 'risk' | 'missing' | 'found';
  description: string;
  source?: {
    document: string;
    page: number;
  };
}

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
                          <td className="p-3 text-sm text-foreground font-mono">{result.number}</td>
                          <td className="p-3 text-sm text-foreground font-medium">{result.name}</td>
                          <td className="p-3 text-sm text-foreground">{result.description}</td>
                          <td className="p-3 text-sm text-muted-foreground">
                            {result.source ? (
                              <span>
                                {result.source.document} (p. {result.source.page})
                              </span>
                            ) : (
                              <span className="italic">Not specified</span>
                            )}
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