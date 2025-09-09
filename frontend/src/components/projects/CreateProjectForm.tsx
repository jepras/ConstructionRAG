"use client"

import { useState } from "react"
import { FileDropzone } from "@/components/upload/FileDropzone"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Globe, Lock, ExternalLink, Shield, Loader2, FolderOpen } from "lucide-react"
import { useCreateProject } from "@/hooks/useApiQueries"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import posthog from 'posthog-js'

interface CreateProjectFormProps {
  onProjectCreated: (projectId: string) => void
}

export function CreateProjectForm({ onProjectCreated }: CreateProjectFormProps) {
  const [files, setFiles] = useState<File[]>([])
  const [projectName, setProjectName] = useState("")
  const [initialVersion, setInitialVersion] = useState("Initial Version")
  const [isPublic, setIsPublic] = useState(true) // Default to public for now
  const [shareWithAI, setShareWithAI] = useState(true)
  const [language, setLanguage] = useState("Danish")
  const [selectedExperts, setSelectedExperts] = useState<string[]>([])
  const [validationComplete, setValidationComplete] = useState(false)
  const [filesAreValid, setFilesAreValid] = useState(false)
  const [hasValidationErrors, setHasValidationErrors] = useState(false)
  const [estimatedTime, setEstimatedTime] = useState(0)
  const [isValidating, setIsValidating] = useState(false)

  const createProjectMutation = useCreateProject()

  const availableExperts = [
    { id: "security", name: "🛡️ Security Tender Expert" },
    { id: "moisture", name: "💧 Moisture Risk Expert" },
    { id: "structural", name: "🏗️ Structural Integrity Analyst" },
    { id: "leed", name: "🏢 LEED Certification Assistant" }
  ]

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(newFiles)
    setValidationComplete(false) // Reset validation state
    setFilesAreValid(false)
    setHasValidationErrors(false)
    setIsValidating(newFiles.length > 0) // Start validating if we have files
  }

  const handleValidationComplete = (isValid: boolean, estimatedMinutes: number) => {
    setValidationComplete(true)
    setFilesAreValid(isValid)
    setEstimatedTime(estimatedMinutes)
    setIsValidating(false) // Validation is complete
  }

  const handleValidationStateChange = (hasErrors: boolean) => {
    setHasValidationErrors(hasErrors)
  }

  const handleRemoveFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index))
  }

  const toggleExpert = (expertId: string) => {
    setSelectedExperts(prev =>
      prev.includes(expertId)
        ? prev.filter(id => id !== expertId)
        : [...prev, expertId]
    )
  }

  const handleSubmit = async () => {
    if (files.length === 0 || !projectName.trim()) {
      return
    }

    // Generate a temporary project ID for immediate redirect
    const tempProjectId = `temp-project-${Date.now()}-${Math.random().toString(36).substring(2)}`

    // Track authenticated project creation immediately
    posthog.capture('project_created', {
      is_authenticated: true,
      upload_type: 'user_project',
      project_name: projectName,
      file_count: files.length,
      total_file_size_mb: Math.round(files.reduce((sum, file) => sum + file.size, 0) / 1024 / 1024 * 100) / 100,
      is_public: isPublic,
      language: language,
      selected_experts: selectedExperts,
      estimated_time_minutes: estimatedTime,
      user_context: 'authenticated'
    })

    // Show success message and redirect immediately
    toast.success(`Project "${projectName}" created successfully!`)
    onProjectCreated(tempProjectId)

    // Create project in background (fire and forget)
    const projectData = {
      name: projectName,
      initial_version_name: initialVersion,
      visibility: isPublic ? 'public' as const : 'private' as const,
      share_with_ai: shareWithAI,
      language,
      expert_modules: selectedExperts,
      files
    }

    createProjectMutation.mutate(projectData, {
      onSuccess: (response) => {
        // Background project creation succeeded - user already redirected
        console.log("Background project creation completed:", response.project_id || response.id)
      },
      onError: (error) => {
        // Background project creation failed - user already redirected, but log the error
        console.error("Background project creation failed:", error)
        // Optionally could show a notification, but user is already on success page
      }
    })
  }

  return (
    <div className="space-y-6">
      {/* Project Details */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <FolderOpen className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">
            Project Details
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="project-name">Project Name*</Label>
            <Input
              id="project-name"
              placeholder="e.g., Downtown Tower Construction"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={createProjectMutation.isPending}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="initial-version">Initial Version Name</Label>
            <Input
              id="initial-version"
              placeholder="e.g., Phase 1 - Bid or As-Built"
              value={initialVersion}
              onChange={(e) => setInitialVersion(e.target.value)}
              disabled={createProjectMutation.isPending}
              className="mt-1"
            />
          </div>
        </div>
      </div>

      {/* Document Upload */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Upload className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">
            Project Documents*
          </h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Upload your construction documents, specifications, drawings, and other project files.
        </p>

        <FileDropzone
          onFilesSelected={handleFilesSelected}
          selectedFiles={files}
          onRemoveFile={handleRemoveFile}
          onValidationComplete={handleValidationComplete}
          onValidationErrors={handleValidationStateChange}
          maxFiles={20}
          disabled={createProjectMutation.isPending}
          showValidation={true}
        />
      </div>

      {/* Project Settings */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">
            Project Settings
          </h2>
          <div className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full">
            <span className="text-xs font-medium">Yet to Come</span>
          </div>
        </div>
        
        <p className="text-sm text-muted-foreground mb-6">
          Advanced project settings will be available soon. For now, projects are created with default settings.
        </p>

        <div className="space-y-4 opacity-60 pointer-events-none">
          <div>
            <Label className="text-sm font-medium mb-2 block">Visibility</Label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled={true}
                className="flex items-center justify-center gap-2 p-3 rounded-lg border bg-primary text-primary-foreground border-primary"
              >
                <Globe className="h-4 w-4" />
                <span className="text-sm font-medium">Public</span>
              </button>
              <button
                type="button"
                disabled={true}
                className="flex items-center justify-center gap-2 p-3 rounded-lg border bg-card border-border opacity-50"
              >
                <Lock className="h-4 w-4" />
                <span className="text-sm font-medium">Private</span>
              </button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Projects are currently created as public by default.
            </p>
          </div>

          <div>
            <Label className="text-sm font-medium mb-2 block">Data Privacy</Label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled={true}
                className="flex items-center justify-center gap-2 p-3 rounded-lg border bg-primary text-primary-foreground border-primary"
              >
                <ExternalLink className="h-4 w-4" />
                <span className="text-sm font-medium">Share with External AI</span>
              </button>
              <button
                type="button"
                disabled={true}
                className="flex items-center justify-center gap-2 p-3 rounded-lg border bg-card border-border opacity-50"
              >
                <Shield className="h-4 w-4" />
                <span className="text-sm font-medium">Keep Data Private</span>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 opacity-60 pointer-events-none">
          <Label className="text-sm font-medium mb-2 block">Expert Modules</Label>
          <p className="text-xs text-muted-foreground mb-3">
            Add specialized AI experts to enhance project analysis.
          </p>
          <div className="grid grid-cols-2 gap-3">
            {availableExperts.map((expert) => (
              <div
                key={expert.id}
                className="flex items-center gap-2 p-3 border border-border rounded-lg bg-muted text-muted-foreground"
              >
                <span className="text-sm">{expert.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-6 opacity-60 pointer-events-none">
          <Label htmlFor="language" className="text-muted-foreground">Project Language</Label>
          <select
            id="language"
            value={language}
            disabled={true}
            className="w-full mt-1 px-3 py-2 bg-muted border border-muted rounded-lg text-muted-foreground"
          >
            <option value="Danish">Danish</option>
          </select>
        </div>
      </div>

      {createProjectMutation.error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
          <p className="text-sm text-destructive">
            {createProjectMutation.error instanceof Error
              ? createProjectMutation.error.message
              : "Failed to create project. Please try again."}
          </p>
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={
          createProjectMutation.isPending ||
          files.length === 0 ||
          !projectName.trim() ||
          isValidating ||
          (files.length > 0 && !validationComplete) ||
          hasValidationErrors
        }
        className="w-full h-12 text-base"
      >
        {createProjectMutation.isPending ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Creating Project...
          </>
        ) : isValidating || (files.length > 0 && !validationComplete) ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Validating Files...
          </>
        ) : hasValidationErrors ? (
          "Fix Validation Errors to Continue"
        ) : estimatedTime > 0 ? (
          `Create Project (~${estimatedTime} min processing)`
        ) : (
          "Create Project"
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