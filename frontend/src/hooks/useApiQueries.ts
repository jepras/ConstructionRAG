"use client"

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

// Upload mutations
export function useUploadFiles() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (formData: FormData) => apiClient.uploadFiles(formData),
    onSuccess: () => {
      // Invalidate indexing runs when new upload completes
      queryClient.invalidateQueries({ queryKey: ['indexing-runs'] })
    },
  })
}

// Indexing queries
export function useIndexingProgress(indexingRunId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['indexing-progress', indexingRunId],
    queryFn: () => indexingRunId ? apiClient.getIndexingProgress(indexingRunId) : null,
    enabled: enabled && !!indexingRunId,
    refetchInterval: (data) => {
      // Stop polling if indexing is complete
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 2000 // Poll every 2 seconds while processing
    },
  })
}

export function useIndexingRun(indexingRunId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['indexing-run', indexingRunId],
    queryFn: () => indexingRunId ? apiClient.getIndexingRun(indexingRunId) : null,
    enabled: enabled && !!indexingRunId,
  })
}

// Public projects queries
export function usePublicProjects(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['public-projects', limit, offset],
    queryFn: () => apiClient.getPublicProjects(limit, offset),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function usePublicProjectsWithWikis(limit = 50) {
  return useQuery({
    queryKey: ['public-projects-with-wikis', limit],
    queryFn: () => apiClient.getPublicProjectsWithWikis(limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useProjectWikiStatus(indexingRunId: string | null) {
  return useQuery({
    queryKey: ['project-wiki-status', indexingRunId],
    queryFn: () => indexingRunId ? apiClient.getProjectWikiStatus(indexingRunId) : null,
    enabled: !!indexingRunId,
  })
}

// Auth queries and mutations
export function useCurrentUser() {
  return useQuery({
    queryKey: ['current-user'],
    queryFn: () => apiClient.getCurrentUser(),
    retry: false, // Don't retry auth failures
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useSignUp() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      apiClient.signUp(email, password),
  })
}

export function useSignIn() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      apiClient.signIn(email, password),
    onSuccess: () => {
      // Refresh user data on successful sign in
      queryClient.invalidateQueries({ queryKey: ['current-user'] })
    },
  })
}

export function useSignOut() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => apiClient.signOut(),
    onSuccess: () => {
      // Clear all user-related queries on sign out
      queryClient.removeQueries({ queryKey: ['current-user'] })
      queryClient.clear() // Optionally clear entire cache
    },
  })
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (email: string) => apiClient.resetPassword(email),
  })
}

// Progressive project loading hooks for client-side navigation
export function useProjectBasic(slug: string | null, enabled = true) {
  return useQuery({
    queryKey: ['project-basic', slug],
    queryFn: () => slug ? apiClient.getProjectFromSlug(slug) : null,
    enabled: enabled && !!slug,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  })
}

export function useProjectWikiRuns(indexingRunId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['project-wiki-runs', indexingRunId],
    queryFn: () => indexingRunId ? apiClient.getWikiRunsByIndexingRun(indexingRunId) : null,
    enabled: enabled && !!indexingRunId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  })
}

export function useProjectWikiPages(wikiRunId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['project-wiki-pages', wikiRunId],
    queryFn: () => wikiRunId ? apiClient.getWikiPages(wikiRunId) : null,
    enabled: enabled && !!wikiRunId,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  })
}

export function useProjectWikiContent(wikiRunId: string | null, pageName: string | null, enabled = true) {
  return useQuery({
    queryKey: ['project-wiki-content', wikiRunId, pageName],
    queryFn: () => (wikiRunId && pageName) ? apiClient.getWikiPageContent(wikiRunId, pageName) : null,
    enabled: enabled && !!wikiRunId && !!pageName,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  })
}

// Prefetching hook for project cards hover
export function usePrefetchProject() {
  const queryClient = useQueryClient()
  
  return (slug: string) => {
    // Prefetch basic project data
    queryClient.prefetchQuery({
      queryKey: ['project-basic', slug],
      queryFn: () => apiClient.getProjectFromSlug(slug),
      staleTime: 10 * 60 * 1000, // 10 minutes
    })
  }
}