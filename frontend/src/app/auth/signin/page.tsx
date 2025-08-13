import { Suspense } from 'react'
import { SignInForm } from '@/components/auth/SignInForm'

function SignInFormWrapper() {
  return <SignInForm />
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    }>
      <SignInFormWrapper />
    </Suspense>
  )
}

export const metadata = {
  title: 'Sign In - ConstructionRAG',
  description: 'Sign in to your ConstructionRAG account',
}