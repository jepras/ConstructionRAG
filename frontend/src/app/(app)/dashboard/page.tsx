'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/components/providers/AuthProvider'
import { useUserProjects } from '@/hooks/useApiQueries'
import { Button } from '@/components/ui/button'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { EmptyProjectsState } from '@/components/projects/EmptyProjectsState'
import { Plus } from 'lucide-react'

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

export default function DashboardPage() {
  const { user, isLoading: authLoading } = useAuth()
  const [showMockData, setShowMockData] = useState(false) // Toggle for demo
  
  // Fetch user projects from API
  const { 
    data: userProjects = [], 
    isLoading: projectsLoading,
    error: projectsError 
  } = useUserProjects()

  if (authLoading || projectsLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  // Use mock data for demo or real data from API
  const projects = showMockData ? mockProjects : userProjects

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
          {projectsError && (
            <p className="text-sm text-destructive">
              Failed to load projects: {projectsError instanceof Error ? projectsError.message : 'Unknown error'}
            </p>
          )}
        </div>

        {projects.length === 0 ? (
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