"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { CreateProjectForm } from "@/components/projects/CreateProjectForm"
import { CheckCircle, ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function NewProjectPage() {
  const [isCreated, setIsCreated] = useState(false)
  
  useEffect(() => {
    document.title = "New Project - specfinder.io";
  }, []);

  const handleProjectCreated = (projectId: string) => {
    setIsCreated(true)
    // Scroll to top for better UX when showing success message
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Breadcrumb Navigation */}
        <div className="mb-8">
          <Link href="/dashboard" className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors">
            <ChevronLeft className="h-4 w-4 mr-1" />
            Back to Dashboard
          </Link>
        </div>

        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Create New Project
          </h1>
          <p className="text-muted-foreground text-lg">
            Start a new construction project by uploading your documents and configuring your settings.
          </p>
        </div>

        {!isCreated ? (
          <CreateProjectForm onProjectCreated={handleProjectCreated} />
        ) : (
          <div className="bg-card border border-border rounded-lg p-8 text-center">
            <div className="flex justify-center mb-6">
              <CheckCircle className="h-16 w-16 text-green-500" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-4">
              Project Created Successfully!
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-6">
              Your project is being processed. We'll generate your AI-powered project wiki from the uploaded documents.
              This process may take a few minutes to complete.
            </p>
            <div className="flex gap-3 justify-center">
              <Link href="/dashboard">
                <Button variant="outline">
                  Back to Dashboard
                </Button>
              </Link>
              <Button>
                View Project Status
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}