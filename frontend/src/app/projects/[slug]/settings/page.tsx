'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient, type IndexingRunWithConfig, type IndexingRunDocument } from '@/lib/api-client';
import { Globe, Lock, FileText, File, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

interface SettingsPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default function SettingsPage({ params }: SettingsPageProps) {
  const [slug, setSlug] = useState<string>('');
  const [indexingRun, setIndexingRun] = useState<IndexingRunWithConfig | null>(null);
  const [documents, setDocuments] = useState<IndexingRunDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const router = useRouter();

  // Handle params properly in client component
  useEffect(() => {
    params.then(({ slug }) => setSlug(slug));
  }, [params]);

  // Fetch indexing run data
  useEffect(() => {
    if (!slug) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        const [runData, documentsData] = await Promise.all([
          apiClient.getIndexingRunWithConfig(slug),
          apiClient.getIndexingRunDocuments(slug.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)?.[0] || '')
        ]);
        setIndexingRun(runData);
        setDocuments(documentsData);
      } catch (err) {
        console.error('API Error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load settings');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [slug]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <div className="h-8 bg-muted rounded w-32 mb-2 animate-pulse"></div>
          <div className="h-4 bg-muted rounded w-96 animate-pulse"></div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-96 bg-muted rounded animate-pulse"></div>
          <div className="h-96 bg-muted rounded animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (error || !indexingRun) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-foreground mb-2">Settings</h1>
          <p className="text-muted-foreground">
            Settings used for the indexing run of version: {indexingRun?.name || 'Unknown'}
          </p>
        </div>
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">
              {error || 'Failed to load indexing run settings'}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const getVisibilityDisplay = () => {
    const isPublic = indexingRun.access_level === 'public' || indexingRun.upload_type === 'email';
    return {
      text: isPublic ? 'Public' : 'Private',
      icon: isPublic ? Globe : Lock,
      className: isPublic ? 'text-primary' : 'text-muted-foreground'
    };
  };

  const getLanguageDisplay = () => {
    const languages = indexingRun?.pipeline_config?.partition?.ocr_languages;
    if (!languages || !Array.isArray(languages)) return 'Auto-detect';
    if (languages.includes('dan')) return 'Danish';
    if (languages.includes('eng')) return 'English';
    return languages.join(', ') || 'Auto-detect';
  };

  const getFileIcon = (filename: string) => {
    const extension = filename.split('.').pop()?.toLowerCase();
    return extension === 'pdf' ? FileText : File;
  };

  const handleDeleteConfirm = async () => {
    if (!indexingRun) return;

    try {
      setIsDeleting(true);
      await apiClient.deleteIndexingRun(indexingRun.id);
      
      toast.success(`Project "${indexingRun.name}" deleted successfully`)
      router.push('/projects');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete indexing run';
      setError(errorMessage);
      toast.error("Failed to delete project. Please try again.");
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const visibility = getVisibilityDisplay();
  const VisibilityIcon = visibility.icon;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">Indexing Configuration</h1>
        <p className="text-muted-foreground">
          Settings used for the indexing run of version: <strong>{indexingRun.name}</strong>
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Configuration Details */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Version Name</span>
              <span className="font-medium">{indexingRun.name}</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Visibility</span>
              <div className="flex items-center gap-2">
                <VisibilityIcon className={`size-4 ${visibility.className}`} />
                <span className="font-medium">{visibility.text}</span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Language</span>
              <div className="flex items-center gap-2">
                <Globe className="size-4 text-muted-foreground" />
                <span className="font-medium">{getLanguageDisplay()}</span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Text Generation LLM</span>
              <div className="flex items-center gap-2">
                <span className="text-lg">✨</span>
                <span className="font-medium">
                  {indexingRun?.pipeline_config?.generation?.model || 'Not configured'}
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Embedding Model</span>
              <div className="flex items-center gap-2">
                <span className="text-lg">🔧</span>
                <span className="font-medium">
                  {indexingRun?.pipeline_config?.embedding?.model || 'Not configured'}
                </span>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">OCR Strategy</span>
              <div className="flex items-center gap-2">
                <span className="text-lg">📄</span>
                <span className="font-medium">
                  {indexingRun?.pipeline_config?.partition?.ocr_strategy || 'Not configured'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Indexed Documents */}
        <Card>
          <CardHeader>
            <CardTitle>Indexed Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {documents && documents.length > 0 ? (
                documents.map((document) => {
                  const FileIcon = getFileIcon(document.filename);
                  return (
                    <div 
                      key={document.id} 
                      className="flex items-center gap-3 p-3 bg-secondary rounded-lg"
                    >
                      <FileIcon className="size-5 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm truncate block">{document.filename}</span>
                        <span className="text-xs text-muted-foreground">
                          {(document.file_size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-muted-foreground text-sm">
                  No documents found for this indexing run
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold mb-2">Delete this indexing run</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Once you delete this run, the generated wiki and all related data will be gone forever.
                This action cannot be undone.
              </p>
            </div>
            <Button 
              variant="destructive" 
              className="shrink-0"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isDeleting}
            >
              <Trash2 className="size-4 mr-2" />
              Delete Indexing Run
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-destructive">Confirm Deletion</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-6">
                Are you sure you want to delete the indexing run "{indexingRun?.name}"? 
                This will permanently delete the generated wiki and all related data. 
                This action cannot be undone.
              </p>
              <div className="flex gap-3 justify-end">
                <Button 
                  variant="outline" 
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button 
                  variant="destructive" 
                  onClick={handleDeleteConfirm}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="size-4 mr-2" />
                      Delete Permanently
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}