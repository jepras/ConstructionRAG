'use client';

import React from 'react';

interface AnalysisResultsProps {
  rawOutput: string;
}

export default function AnalysisResults({ rawOutput }: AnalysisResultsProps) {
  return (
    <div className="space-y-4">
      <div className="bg-secondary/50 border border-border rounded-lg p-4">
        <h3 className="text-sm font-medium text-foreground mb-2">Raw LLM Analysis Output</h3>
        <div className="bg-background border border-border rounded p-3 max-h-96 overflow-y-auto">
          <pre className="text-sm text-foreground whitespace-pre-wrap font-mono">
            {rawOutput}
          </pre>
        </div>
      </div>
    </div>
  );
}