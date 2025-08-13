'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import { apiClient, type User } from '@/lib/api-client'
import { useLocalStorage } from '@/hooks/useLocalStorage'

export interface AnonymousSession {
  uploadedDocuments: string[]
  indexingRunId: string | null
  queries: { id: string; query: string; timestamp: string }[]
}

export interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  anonymousSession: AnonymousSession | null
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signUp: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  signOut: () => Promise<void>
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>
  updateAnonymousSession: (session: Partial<AnonymousSession>) => void
  migrateAnonymousSession: () => Promise<void>
}

const AuthContext = createContext<AuthState | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [anonymousSession, setAnonymousSession] = useLocalStorage<AnonymousSession | null>('anonymous_session', null)
  const supabase = createClient()

  // Initialize anonymous session if it doesn't exist
  useEffect(() => {
    if (!anonymousSession) {
      setAnonymousSession({
        uploadedDocuments: [],
        indexingRunId: null,
        queries: [],
      })
    }
  }, [anonymousSession, setAnonymousSession])

  const updateAnonymousSession = (updates: Partial<AnonymousSession>) => {
    setAnonymousSession(prev => prev ? { ...prev, ...updates } : {
      uploadedDocuments: [],
      indexingRunId: null,
      queries: [],
      ...updates,
    } as AnonymousSession)
  }

  const migrateAnonymousSession = async () => {
    if (!user || !anonymousSession) return

    try {
      // Here we would call an API endpoint to migrate anonymous data
      // For now, we'll just clear the anonymous session
      console.log('Migrating anonymous session for user:', user.id, anonymousSession)
      
      // TODO: Implement migration API call
      // await apiClient.migrateAnonymousSession(user.id, anonymousSession)
      
      // Clear anonymous session after migration
      setAnonymousSession(null)
    } catch (error) {
      console.error('Failed to migrate anonymous session:', error)
    }
  }

  const signIn = async (email: string, password: string) => {
    try {
      setIsLoading(true)
      
      // First sign in with Supabase
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) {
        return { success: false, error: error.message }
      }

      if (data.user) {
        // Get user profile from our backend
        try {
          const userProfile = await apiClient.getCurrentUser()
          setUser(userProfile)
          
          // Migrate anonymous session if it exists
          await migrateAnonymousSession()
          
          return { success: true }
        } catch (profileError) {
          console.error('Failed to get user profile:', profileError)
          return { success: false, error: 'Failed to load user profile' }
        }
      }

      return { success: false, error: 'Unknown error occurred' }
    } catch (error) {
      console.error('Sign in error:', error)
      return { success: false, error: 'Sign in failed' }
    } finally {
      setIsLoading(false)
    }
  }

  const signUp = async (email: string, password: string) => {
    try {
      setIsLoading(true)

      // Use Supabase for signup
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`
        }
      })

      if (error) {
        return { success: false, error: error.message }
      }

      if (data.user) {
        return { success: true }
      }

      return { success: false, error: 'Unknown error occurred' }
    } catch (error) {
      console.error('Sign up error:', error)
      return { success: false, error: 'Sign up failed' }
    } finally {
      setIsLoading(false)
    }
  }

  const signOut = async () => {
    try {
      console.log('Starting sign out process...')
      setIsLoading(true)
      
      // Sign out from Supabase
      const { error } = await supabase.auth.signOut()
      if (error) {
        console.error('Supabase sign out error:', error)
        throw error
      }
      
      console.log('Successfully signed out from Supabase')
      
      // Clear user state
      setUser(null)
      
      // Reinitialize anonymous session
      setAnonymousSession({
        uploadedDocuments: [],
        indexingRunId: null,
        queries: [],
      })
      
      console.log('Sign out completed successfully')
    } catch (error) {
      console.error('Sign out error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const resetPassword = async (email: string) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email)
      
      if (error) {
        return { success: false, error: error.message }
      }
      
      return { success: true }
    } catch (error) {
      console.error('Reset password error:', error)
      return { success: false, error: 'Failed to send reset email' }
    }
  }

  // Listen for auth state changes
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      setIsLoading(true)
      
      if (session?.user) {
        try {
          // Get user profile from our backend
          const userProfile = await apiClient.getCurrentUser()
          setUser(userProfile)
        } catch (error) {
          console.error('Failed to get user profile on auth change:', error)
          setUser(null)
        }
      } else {
        setUser(null)
      }
      
      setIsLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [supabase.auth])

  // Check if user is already signed in on mount
  useEffect(() => {
    const checkUser = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        
        if (session?.user) {
          try {
            const userProfile = await apiClient.getCurrentUser()
            setUser(userProfile)
          } catch (error) {
            console.error('Failed to get user profile on mount:', error)
            setUser(null)
          }
        }
      } catch (error) {
        console.error('Error checking auth state:', error)
      } finally {
        setIsLoading(false)
      }
    }

    checkUser()
  }, [supabase.auth])

  const value: AuthState = {
    user,
    isLoading,
    isAuthenticated: !!user,
    anonymousSession,
    signIn,
    signUp,
    signOut,
    resetPassword,
    updateAnonymousSession,
    migrateAnonymousSession,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}