'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/providers/AuthProvider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function DashboardPage() {
  const { user, signOut, isLoading } = useAuth()
  const router = useRouter()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const handleSignOut = async () => {
    try {
      await signOut()
      // Redirect to homepage after successful sign out
      router.push('/')
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>

        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card className="bg-card border-supabase-border">
            <CardHeader>
              <CardTitle className="text-foreground">Welcome Back!</CardTitle>
              <CardDescription className="text-muted-foreground">
                You&apos;re signed in as: {user?.email}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                User ID: {user?.id}
              </p>
              {user?.profile?.full_name && (
                <p className="text-muted-foreground mt-2">
                  Name: {user.profile.full_name}
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card border-supabase-border">
            <CardHeader>
              <CardTitle className="text-foreground">Projects</CardTitle>
              <CardDescription className="text-muted-foreground">
                Manage your construction projects
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Projects feature coming soon...
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card border-supabase-border">
            <CardHeader>
              <CardTitle className="text-foreground">Documents</CardTitle>
              <CardDescription className="text-muted-foreground">
                Upload and manage documents
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Document management coming soon...
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}