'use client';

import React, { useEffect, useState } from 'react';
import { ChevronRight, FileText, Files, Clock, Image, Table, Search } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface IndexingSummaryBarProps {
  indexingRunId: string;
}

interface SummaryData {
  pdfCount: number;
  pdfNames: string[];
  pageCount: number;
  imageCount: number;
  tableCount: number;
  chunkCount: number;
  lastUpdated: string;
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days !== 1 ? 's' : ''} ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} month${months !== 1 ? 's' : ''} ago`;
  const years = Math.floor(months / 12);
  return `${years} year${years !== 1 ? 's' : ''} ago`;
}

function formatNumber(num: number): string {
  return num.toLocaleString();
}

function IndexingSummaryBarSkeleton() {
  return (
    <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
      <div className="flex items-center gap-6 text-sm mb-3">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-24 ml-auto" />
      </div>
      <Skeleton className="h-6 w-32" />
    </div>
  );
}

export default function IndexingSummaryBar({ indexingRunId }: IndexingSummaryBarProps) {
  const [data, setData] = useState<SummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Fetch progress data after mount to not block initial render
    const fetchData = async () => {
      try {
        const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${baseURL}/api/indexing-runs/${indexingRunId}/summary`);
        if (!response.ok) {
          throw new Error('Failed to fetch progress data');
        }
        const summaryData = await response.json();

        setData({
          pdfCount: summaryData.pdf_count,
          pdfNames: summaryData.pdf_names,
          pageCount: summaryData.total_pages,
          imageCount: summaryData.total_images,
          tableCount: summaryData.total_tables,
          chunkCount: summaryData.total_chunks,
          lastUpdated: summaryData.last_updated || new Date().toISOString(),
        });
      } catch (error) {
        console.error('Failed to fetch indexing summary:', error);
        // Fail silently - don't show the summary bar if data can't be loaded
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [indexingRunId]);

  if (isLoading) {
    return <IndexingSummaryBarSkeleton />;
  }

  if (!data) {
    return null; // Fail silently if no data
  }

  return (
    <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
      {/* Stats Row */}
      <div className="flex flex-wrap items-center gap-4 md:gap-6 text-sm mb-3">
        {data.pageCount > 0 && (
          <span className="flex items-center gap-1.5 text-foreground">
            <Files className="h-4 w-4 text-muted-foreground" />
            {formatNumber(data.pageCount)} pages
          </span>
        )}
        {data.imageCount > 0 && (
          <span className="flex items-center gap-1.5 text-foreground">
            <Image className="h-4 w-4 text-muted-foreground" />
            {formatNumber(data.imageCount)} images
          </span>
        )}
        {data.tableCount > 0 && (
          <span className="flex items-center gap-1.5 text-foreground">
            <Table className="h-4 w-4 text-muted-foreground" />
            {formatNumber(data.tableCount)} tables
          </span>
        )}
        {data.chunkCount > 0 && (
          <span className="flex items-center gap-1.5 text-foreground">
            <Search className="h-4 w-4 text-muted-foreground" />
            {formatNumber(data.chunkCount)} chunks
          </span>
        )}
        <span className="flex items-center gap-1.5 text-muted-foreground ml-auto">
          <Clock className="h-3.5 w-3.5" />
          Updated {formatTimeAgo(data.lastUpdated)}
        </span>
      </div>

      {/* GitHub-style PDF Collapsible */}
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger className="flex items-center gap-2 text-sm hover:text-foreground transition-colors">
          <ChevronRight 
            className={cn(
              "h-4 w-4 transition-transform duration-200",
              isOpen && "rotate-90"
            )} 
          />
          <span className="font-medium text-foreground">
            PDF count: {data.pdfCount}
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2">
          {/* Show first PDF by default */}
          {data.pdfNames.length > 0 && (
            <div className="ml-6 mb-2">
              <div className="py-1 text-sm text-muted-foreground">
                <FileText className="inline-block h-3.5 w-3.5 mr-2" />
                {data.pdfNames[0]}
              </div>
            </div>
          )}
          {/* Show remaining PDFs when expanded */}
          {data.pdfNames.length > 1 && (
            <div className="ml-6 space-y-1 max-h-48 overflow-y-auto">
              {data.pdfNames.slice(1).map((pdfName, index) => (
                <div 
                  key={index + 1} 
                  className="py-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <FileText className="inline-block h-3.5 w-3.5 mr-2" />
                  {pdfName}
                </div>
              ))}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}