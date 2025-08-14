'use client'

import React, { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/components/providers/AuthProvider'
import { toast } from 'sonner'

export function SignInForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  const { signIn } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectTo = searchParams.get('redirectTo') || '/dashboard'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const result = await signIn(email, password)
      
      if (result.success) {
        toast.success('Welcome back!')
        router.push(redirectTo)
      } else {
        setError(result.error || 'Sign in failed')
      }
    } catch {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDevSignIn = async () => {
    setError('')
    setIsLoading(true)

    try {
      const result = await signIn('jeprasher@gmail.com', 'Test123!')
      
      if (result.success) {
        toast.success('Welcome back!')
        router.push(redirectTo)
      } else {
        setError(result.error || 'Dev sign in failed')
      }
    } catch {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md bg-card border-border">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-foreground text-center">
            Sign In
          </CardTitle>
          <CardDescription className="text-muted-foreground text-center">
            Enter your email and password to access your account
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-md">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-foreground">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-input border-border text-foreground placeholder:text-muted-foreground focus:border-ring"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-foreground">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-input border-border text-foreground placeholder:text-muted-foreground focus:border-ring"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4 pt-6">
            <Button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
            
            {/* Development Sign In Button */}
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleDevSignIn}
              disabled={isLoading}
            >
              🚀 Dev Sign In (jeprasher@gmail.com)
            </Button>
            
            <div className="text-center space-y-2">
              <Link
                href="/auth/reset-password"
                className="text-sm text-primary hover:text-primary/90 transition-colors"
              >
                Forgot your password?
              </Link>
              <div className="text-sm text-muted-foreground">
                Don&apos;t have an account?{' '}
                <Link
                  href="/auth/signup"
                  className="text-primary hover:text-primary/90 transition-colors"
                >
                  Sign up
                </Link>
              </div>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}