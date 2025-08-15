"use client"

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useState } from 'react'

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
        retry: (failureCount, error: any) => {
          // Don't retry on 404s, auth errors, or client errors
          if (error?.status === 404 || error?.status === 401 || error?.status === 403) {
            return false
          }
          // Don't retry on API client errors (auth token issues)
          if (error?.message?.includes('API Error') || error?.message?.includes('Failed to get user profile')) {
            return false
          }
          return failureCount < 3
        },
        refetchOnWindowFocus: false, // Disable automatic refetch on window focus
      },
      mutations: {
        retry: false, // Don't retry mutations by default
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}