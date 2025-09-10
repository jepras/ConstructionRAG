'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuth } from '@/components/providers/AuthProvider'
import { toast } from 'sonner'

export function SignUpForm() {
  const [step, setStep] = useState(1)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [selectedPlan, setSelectedPlan] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  
  const { signUp } = useAuth()
  const router = useRouter()

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Basic validation for step 1
    if (!email || !password || !confirmPassword || !selectedPlan) {
      setError('Please fill in all fields')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long')
      return
    }

    // Move to step 2
    setStep(2)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(false)

    setIsLoading(true)

    try {
      const result = await signUp(email, password)
      
      if (result.success) {
        toast.success('Account created! Check your email to verify.')
        setSuccess(true)
        // Don't redirect immediately - user needs to confirm email
      } else {
        setError(result.error || 'Sign up failed')
      }
    } catch {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-md space-y-8">
          {/* Branding */}
          <div className="text-center space-y-3">
            <div className="flex justify-center">
              <Image
                src="/favicon-32x32.png"
                alt="Specfinder"
                width={48}
                height={48}
                className="w-12 h-12"
                priority
              />
            </div>
            <h1 className="text-3xl font-semibold text-foreground">
              specfinder<span className="text-orange-500">.io</span>
            </h1>
          </div>
          
          <Card className="w-full bg-card border-border">
            <CardHeader className="space-y-1 text-center">
              <CardTitle className="text-2xl font-bold text-foreground">
                Check Your Email
              </CardTitle>
            <CardDescription className="text-muted-foreground">
              We&apos;ve sent you a confirmation link at {email}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="p-3 text-sm text-primary bg-primary/10 border border-primary/20 rounded-md text-center">
              Please check your email and click the confirmation link to activate your account.<br />Also check your spam - especially if your are using Outlook.
            </div>
          </CardContent>
          <CardFooter>
            <Button
              onClick={() => router.push('/auth/signin')}
              variant="secondary"
              className="w-full"
            >
              Back to Sign In
            </Button>
          </CardFooter>
        </Card>
        </div>
      </div>
    )
  }

  if (step === 1) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-md space-y-8">
          {/* Branding */}
          <div className="text-center space-y-3">
            <div className="flex justify-center">
              <Image
                src="/favicon-32x32.png"
                alt="Specfinder"
                width={48}
                height={48}
                className="w-12 h-12"
                priority
              />
            </div>
            <h1 className="text-3xl font-semibold text-foreground">
              specfinder<span className="text-orange-500">.io</span>
            </h1>
          </div>
          
          <Card className="w-full bg-card border-border">
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-bold text-foreground text-center">
                Choose Your Plan
              </CardTitle>
            <CardDescription className="text-muted-foreground text-center">
              Select a plan and enter your account details
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleNext}>
            <CardContent className="space-y-4">
              {error && (
                <div className="p-3 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-md">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="plan" className="text-foreground">
                  Plan
                </Label>
                <Select value={selectedPlan} onValueChange={setSelectedPlan} required>
                  <SelectTrigger className="bg-input border-border text-foreground focus:border-ring">
                    <SelectValue placeholder="Select a plan" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pay-per-project">Pay per project</SelectItem>
                    <SelectItem value="pro">Pro</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  <Link href="/pricing" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors">
                    Read about the different plans here
                  </Link>
                </p>
              </div>
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
                  minLength={6}
                  className="bg-input border-border text-foreground placeholder:text-muted-foreground focus:border-ring"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-foreground">
                  Confirm Password
                </Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="bg-input border-border text-foreground placeholder:text-muted-foreground focus:border-ring"
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4 pt-6">
              <Button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                Next
              </Button>
              <div className="text-center text-sm text-muted-foreground">
                Already have an account?{' '}
                <Link
                  href="/auth/signin"
                  className="text-primary hover:text-primary/90 transition-colors"
                >
                  Sign in
                </Link>
              </div>
            </CardFooter>
          </form>
        </Card>
        </div>
      </div>
    )
  }

  if (step === 2) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-md space-y-8">
          {/* Branding */}
          <div className="text-center space-y-3">
            <div className="flex justify-center">
              <Image
                src="/favicon-32x32.png"
                alt="Specfinder"
                width={48}
                height={48}
                className="w-12 h-12"
                priority
              />
            </div>
            <h1 className="text-3xl font-semibold text-foreground">
              specfinder<span className="text-orange-500">.io</span>
            </h1>
          </div>
          
          <Card className="w-full bg-card border-border">
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-bold text-foreground text-center">
                Beta Access
              </CardTitle>
            <CardDescription className="text-muted-foreground text-center">
              Get free access during our beta period
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {error && (
                <div className="p-3 text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-md">
                  {error}
                </div>
              )}
              <div className="p-4 text-sm text-foreground bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-md">
                <p className="mb-2 font-medium">Great news!</p>
                <p>
                  The app is still in beta, so you can gain access for free for a bit longer, 
                  but we&apos;ll stop your access within the next month and ask you to pay to use the service.
                </p>
              </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4 pt-6">
              <Button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
                disabled={isLoading}
              >
                {isLoading ? 'Creating account...' : 'Create Account for Free'}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => setStep(1)}
              >
                Back
              </Button>
            </CardFooter>
          </form>
        </Card>
        </div>
      </div>
    )
  }

  return null
}