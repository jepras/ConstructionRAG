"use client"

import { useState } from "react"
import { FileDropzone } from "./FileDropzone"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Globe, Lock, ExternalLink, Shield, Loader2 } from "lucide-react"
import { useUploadFiles } from "@/hooks/useApiQueries"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

interface UploadFormProps {
  onUploadComplete: (indexingRunId: string) => void
}

export function UploadForm({ onUploadComplete }: UploadFormProps) {
  const [files, setFiles] = useState<File[]>([])
  const [email, setEmail] = useState("")
  const [isPublic] = useState(true) // Always true for public upload form
  const [shareWithAI] = useState(true) // Always true for public upload form
  const [language, setLanguage] = useState("Danish")
  const [validationComplete, setValidationComplete] = useState(false)
  const [filesAreValid, setFilesAreValid] = useState(false)
  const [estimatedTime, setEstimatedTime] = useState(0)
  
  const uploadMutation = useUploadFiles()

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(newFiles)
    uploadMutation.reset() // Clear any previous errors
    setValidationComplete(false) // Reset validation state
    setFilesAreValid(false)
  }
  
  const handleValidationComplete = (isValid: boolean, estimatedMinutes: number) => {
    setValidationComplete(true)
    setFilesAreValid(isValid)
    setEstimatedTime(estimatedMinutes)
  }

  const handleRemoveFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (files.length === 0) {
      return // Validation handled by button disabled state
    }

    if (!email || !email.includes("@")) {
      return // Validation handled by button disabled state
    }

    // Upload files
    const formData = new FormData()
    files.forEach(file => {
      formData.append("files", file)
    })
    formData.append("email", email)
    formData.append("upload_type", "email")

    uploadMutation.mutate(formData, {
      onSuccess: (response) => {
        toast.success("Documents uploaded and processing started!")
        if (response.index_run_id) {
          onUploadComplete(response.index_run_id)
        }
      },
      onError: (error) => {
        console.error("Upload error:", error)
        toast.error("Failed to upload documents. Please try again.")
      }
    })
  }

  return (
    <div className="space-y-6">
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Upload className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">
            Drop your project folder or PDFs
          </h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Visitors can upload a maximum of 5 PDFs. Unlimited (within reason) for users.
        </p>

        <FileDropzone
          onFilesSelected={handleFilesSelected}
          selectedFiles={files}
          onRemoveFile={handleRemoveFile}
          onValidationComplete={handleValidationComplete}
          disabled={uploadMutation.isPending}
          showValidation={true}
        />
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <div className="space-y-4">

          <div className="space-y-4">
            <div>
              <Label className="text-sm font-medium mb-2 block">Visibility</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setIsPublic(true)}
                  disabled={uploadMutation.isPending}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border transition-all",
                    isPublic 
                      ? "bg-primary text-primary-foreground border-primary" 
                      : "bg-card border-border hover:bg-secondary"
                  )}
                >
                  <Globe className="h-4 w-4" />
                  <span className="text-sm font-medium">Public</span>
                </button>
                <button
                  type="button"
                  disabled={true}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border transition-all relative opacity-50 cursor-not-allowed",
                    "bg-card border-border"
                  )}
                >
                  <Lock className="h-4 w-4" />
                  <span className="text-sm font-medium">Private</span>
                  <span className="absolute -top-2 -right-2 px-1.5 py-0.5 bg-primary text-primary-foreground text-xs rounded">
                    PRO
                  </span>
                </button>
              </div>
            </div>

            <div>
              <Label className="text-sm font-medium mb-2 block">Data Privacy</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setShareWithAI(true)}
                  disabled={uploadMutation.isPending}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border transition-all",
                    shareWithAI 
                      ? "bg-primary text-primary-foreground border-primary" 
                      : "bg-card border-border hover:bg-secondary"
                  )}
                >
                  <ExternalLink className="h-4 w-4" />
                  <span className="text-sm font-medium">Share with External AI</span>
                </button>
                <button
                  type="button"
                  disabled={true}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border transition-all relative opacity-50 cursor-not-allowed",
                    "bg-card border-border"
                  )}
                >
                  <Shield className="h-4 w-4" />
                  <span className="text-sm font-medium">Keep Data Private</span>
                  <span className="absolute -top-2 -right-2 px-1.5 py-0.5 bg-primary text-primary-foreground text-xs rounded">
                    PRO
                  </span>
                </button>
              </div>
            </div>
          </div>

          <div className="opacity-60 pointer-events-none">
            <Label className="text-sm font-medium mb-2 block">Expert Modules <span className="text-xs text-primary">PRO</span></Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-muted border border-border rounded-lg">
                <span className="text-sm text-muted-foreground">🛡️ Security Tender Expert</span>
              </div>
              <div className="p-3 bg-muted border border-border rounded-lg">
                <span className="text-sm text-muted-foreground">💧 Moisture Risk Expert</span>
              </div>
              <div className="p-3 bg-muted border border-border rounded-lg">
                <span className="text-sm text-muted-foreground">🏗️ Structural Integrity Analyst</span>
              </div>
              <div className="p-3 bg-muted border border-border rounded-lg">
                <span className="text-sm text-muted-foreground">🏢 LEED Certification Assistant</span>
              </div>
            </div>
          </div>

          <div className="space-y-3 opacity-60 pointer-events-none">
            <div>
              <Label className="text-sm font-medium mb-2 block text-muted-foreground">Custom Checklist <span className="text-xs text-primary">PRO</span></Label>
              <Button variant="outline" className="w-full bg-muted text-muted-foreground border-muted" disabled>
                + Add Checks
              </Button>
            </div>

            <div>
              <Label className="text-sm font-medium mb-2 block text-muted-foreground">Best Practice Docs <span className="text-xs text-primary">PRO</span></Label>
              <div className="p-8 border-2 border-dashed border-muted rounded-lg text-center bg-muted/20">
                <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">Click to upload or drag and drop</p>
                <p className="text-xs text-muted-foreground mt-1">PDF files only</p>
              </div>
            </div>
          </div>

          <div>
            <Label htmlFor="language">Project Language</Label>
            <select
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={uploadMutation.isPending}
              className="w-full mt-1 px-3 py-2 bg-input border border-border rounded-lg text-foreground"
            >
              <option value="Danish">Danish</option>
            </select>
          </div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-6">
        <p className="text-sm text-muted-foreground mb-4">
          It might take a few hours for our AI to crunch your PDFs, images & tables, depending on the content.
          Add your email and you can test this first thing tomorrow with your morning coffee on site!
        </p>
        <div>
          <Label htmlFor="email">Email *</Label>
          <Input
            id="email"
            type="email"
            placeholder="your.email@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={uploadMutation.isPending}
            className="mt-1"
            required
          />
        </div>
      </div>

      {uploadMutation.error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
          <p className="text-sm text-destructive">
            {uploadMutation.error instanceof Error 
              ? uploadMutation.error.message 
              : "Failed to upload files. Please try again."}
          </p>
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={
          uploadMutation.isPending || 
          files.length === 0 || 
          !email ||
          (files.length > 0 && (!validationComplete || !filesAreValid))
        }
        className="w-full h-12 text-base"
      >
        {uploadMutation.isPending ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Indexing Repository...
          </>
        ) : files.length > 0 && !validationComplete ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Validating Files...
          </>
        ) : files.length > 0 && !filesAreValid ? (
          "Fix Validation Errors to Continue"
        ) : estimatedTime > 0 ? (
          `Index Repository (~${estimatedTime} min)`
        ) : (
          "Index Repository"
        )}
      </Button>
    </div>
  )
}

const Upload = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
)