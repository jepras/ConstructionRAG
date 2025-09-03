'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/components/providers/AuthProvider'
import { useUserProjectsWithWikis } from '@/hooks/useApiQueries'
import { Button } from '@/components/ui/button'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { EmptyProjectsState } from '@/components/projects/EmptyProjectsState'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'
import { Plus } from 'lucide-react'

// Utility function to transform backend project data to frontend ProjectCard format
function transformUserProject(backendProject: any) {
  const projectName = backendProject.project_name || 'Unnamed Project'
  const projectId = backendProject.id
  const indexingRunId = backendProject.indexing_run_id

  // Generate nested slug: project-name-{project_id}/{indexing_run_id}
  const projectSlug = `${projectName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')}-${projectId}`
  const slug = `${projectSlug}/${indexingRunId}`

  // Map backend status to frontend status
  let status: 'processing' | 'wiki_generated' | 'failed' | 'no_documents' = 'no_documents'
  if (backendProject.wiki_status === 'completed') {
    status = 'wiki_generated'
  } else if (backendProject.wiki_status === 'running' || backendProject.wiki_status === 'pending') {
    status = 'processing'
  } else if (backendProject.wiki_status === 'failed') {
    status = 'failed'
  }

  return {
    id: projectId,
    name: projectName,
    slug: slug,
    status: status,
    documentCount: backendProject.pages_count || 1, // Use pages_count as proxy for document count
    createdAt: backendProject.created_at || new Date().toISOString(),
    lastUpdated: backendProject.updated_at
  }
}

// Demo mock data removed

function DashboardContent() {
  const { isLoading: authLoading } = useAuth()
  const [refreshKey, setRefreshKey] = useState(0) // Force refresh on delete

  // Fetch user projects with wikis from API - only when authenticated
  const {
    data: backendProjects = [],
    isLoading: projectsLoading,
    error: projectsError,
    refetch
  } = useUserProjectsWithWikis(50, 0, refreshKey) // Pass refreshKey as dependency

  // Transform backend projects to frontend format
  const transformedProjects = backendProjects.map(transformUserProject)

  // Show loading only during initial auth check
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  // Always use transformed real data from API
  const projects = transformedProjects

  // Handle project deletion
  const handleProjectDelete = () => {
    // Force refetch of projects
    if (refetch) {
      refetch()
    } else {
      // Fallback: increment refresh key to trigger re-render
      setRefreshKey(prev => prev + 1)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Projects</h1>
            <p className="text-muted-foreground">
              Select a project to view its DeepWiki or create a new one.
            </p>
          </div>
          <Link href="/dashboard/new-project">
            <Button size="lg" className="gap-2">
              <Plus className="h-4 w-4" />
              New Project
            </Button>
          </Link>
        </div>

        <div className="mb-6 flex items-center gap-3">
          {projectsLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
              Loading projects...
            </div>
          )}
          {projectsError && (
            <p className="text-sm text-destructive">
              Failed to load projects: {projectsError instanceof Error ? projectsError.message : 'Unknown error'}
            </p>
          )}
        </div>

        {projects.length === 0 && !projectsLoading ? (
          <EmptyProjectsState />
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={handleProjectDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <ErrorBoundary>
      <DashboardContent />
    </ErrorBoundary>
  )
}