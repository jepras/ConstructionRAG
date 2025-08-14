"use client"

import { useEffect, useState } from "react"
import { CheckCircle, Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface IndexingProgressProps {
  indexingRunId: string
  onComplete: () => void
}

export function IndexingProgress({ indexingRunId, onComplete }: IndexingProgressProps) {
  const [status, setStatus] = useState<string>("processing")
  const [progress, setProgress] = useState<any>(null)

  useEffect(() => {
    const checkProgress = async () => {
      try {
        const progressData = await apiClient.getIndexingProgress(indexingRunId)
        setProgress(progressData)
        setStatus(progressData.status)

        if (progressData.status === "completed" || progressData.status === "failed") {
          clearInterval(intervalId)
          if (progressData.status === "completed") {
            setTimeout(onComplete, 2000) // Show success for 2 seconds
          }
        }
      } catch (error) {
        console.error("Error checking progress:", error)
      }
    }

    // Check immediately
    checkProgress()

    // Then check every 3 seconds
    const intervalId = setInterval(checkProgress, 3000)

    return () => clearInterval(intervalId)
  }, [indexingRunId, onComplete])

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-card border border-border rounded-lg p-12 text-center">
        {status === "completed" ? (
          <>
            <CheckCircle className="h-16 w-16 text-primary mx-auto mb-6" />
            <h2 className="text-3xl font-bold text-foreground mb-4">
              We are on it!
            </h2>
            <p className="text-muted-foreground text-lg leading-relaxed">
              We are creating your first generic overview with your documents. We know
              all workers have different needs, which is why we have our expert modules.
              However, they require quite some maintenance so they are behind a paywall.
              If you want to see what it looks like, then you can see an{" "}
              <a href="/projects/example" className="text-primary hover:underline">
                example project here
              </a>
              . See you tomorrow!
            </p>
          </>
        ) : status === "failed" ? (
          <>
            <div className="h-16 w-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-2xl">❌</span>
            </div>
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Something went wrong
            </h2>
            <p className="text-muted-foreground text-lg">
              We encountered an error while processing your documents. Please try again or contact support.
            </p>
          </>
        ) : (
          <>
            <Loader2 className="h-16 w-16 text-primary mx-auto mb-6 animate-spin" />
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Indexing Ongoing...
            </h2>
            <p className="text-muted-foreground text-lg mb-6">
              We're processing your documents and creating your AI-powered project wiki.
              This usually takes a few minutes depending on the size of your documents.
            </p>
            {progress && (
              <div className="space-y-4">
                <div className="bg-background rounded-lg p-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="text-foreground font-medium">
                      {progress.current_step || "Starting..."}
                    </span>
                  </div>
                  {progress.progress_percentage !== undefined && (
                    <div className="w-full bg-secondary rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all duration-500"
                        style={{ width: `${progress.progress_percentage}%` }}
                      />
                    </div>
                  )}
                </div>
                {progress.documents_processed !== undefined && (
                  <p className="text-sm text-muted-foreground">
                    Documents processed: {progress.documents_processed} / {progress.total_documents}
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}