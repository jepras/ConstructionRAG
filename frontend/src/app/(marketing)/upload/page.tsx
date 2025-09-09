"use client"

import { useState, useEffect } from "react"
import { UploadForm } from "@/components/upload/UploadForm"
import { CheckCircle } from "lucide-react"

export default function UploadPage() {
  const [isUploaded, setIsUploaded] = useState(false)
  
  useEffect(() => {
    document.title = "Upload - specfinder.io";
  }, []);

  const handleUploadComplete = (runId: string) => {
    setIsUploaded(true)
  }

  // Scroll to top when isUploaded becomes true
  useEffect(() => {
    if (isUploaded) {
      // Use requestAnimationFrame to ensure DOM is updated
      requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      })
    }
  }, [isUploaded])

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Index your first project
          </h1>
          <p className="text-muted-foreground text-lg">
            Get a taste of our platform's power. Upload documents, provide an email, and we'll notify
            you when your AI-powered project wiki is ready to explore.
          </p>
        </div>

        {!isUploaded ? (
          <UploadForm onUploadComplete={handleUploadComplete} />
        ) : (
          <div className="bg-card border border-border rounded-lg p-8 text-center">
            <div className="flex justify-center mb-6">
              <CheckCircle className="h-16 w-16 text-green-500" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-4">
              We are on it!
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              In the meantime, you can look through our{" "}
              <a href="/projects" className="text-primary hover:underline">
                public projects
              </a>{" "}
              and test out the chat feature on the public projects or see the features we offer for users on the{" "}
              <a href="/pricing" className="text-primary hover:underline">
                pricing page
              </a>.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}