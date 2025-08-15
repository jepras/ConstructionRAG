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
  
  // Generate slug: project-name-{project_id}
  const slug = `${projectName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')}-${projectId}`
  
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

// Mock data - replace with real API call later
const mockProjects = [
  {
    id: 'downtown-tower',
    name: 'Downtown Tower',
    slug: 'downtown-tower-abc123-def4-5678-9abc-def123456789',
    status: 'wiki_generated' as const,
    documentCount: 3,
    createdAt: '2024-01-15T10:00:00Z',
    lastUpdated: '2024-01-16T14:30:00Z'
  },
  {
    id: 'suburban-mall',
    name: 'Suburban Mall Extension',
    slug: 'suburban-mall-def456-abc7-8901-2def-abc456789012',
    status: 'wiki_generated' as const,
    documentCount: 1,
    createdAt: '2024-01-10T09:00:00Z',
    lastUpdated: '2024-01-11T16:45:00Z'
  },
  {
    id: 'new-bridge',
    name: 'New Bridge Construction',
    status: 'no_documents' as const,
    documentCount: 0,
    createdAt: '2024-01-20T11:00:00Z'
  },
  {
    id: 'meridian-heights',
    name: 'Meridian Heights Development',
    slug: 'meridian-heights-ghi789-def0-1234-5ghi-def789012345',
    status: 'wiki_generated' as const,
    documentCount: 3,
    createdAt: '2024-01-05T08:00:00Z',
    lastUpdated: '2024-01-06T12:20:00Z'
  },
  {
    id: 'heerup-skole',
    name: 'Heerup Skole',
    slug: 'heerup-skole-jkl012-ghi3-4567-8jkl-ghi012345678',
    status: 'wiki_generated' as const,
    documentCount: 3,
    createdAt: '2024-01-01T07:00:00Z',
    lastUpdated: '2024-01-02T13:15:00Z'
  }
]

function DashboardContent() {
  const { isLoading: authLoading } = useAuth()
  const [showMockData, setShowMockData] = useState(false) // Toggle for demo
  
  // Fetch user projects with wikis from API - only when authenticated
  const { 
    data: backendProjects = [], 
    isLoading: projectsLoading,
    error: projectsError 
  } = useUserProjectsWithWikis(50, 0)

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

  // Use mock data for demo or transformed real data from API
  const projects = showMockData ? mockProjects : transformedProjects

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

        {/* Demo toggle button - remove in production */}
        <div className="mb-6 flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setShowMockData(!showMockData)}
            className="text-xs"
          >
            {showMockData ? 'Hide Demo Projects' : 'Show Demo Projects'}
          </Button>
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
              <ProjectCard key={project.id} project={project} />
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