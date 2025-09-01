"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { FileText, CheckCircle, Clock, AlertCircle, FolderOpen, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"

interface ProjectCardProps {
  project: {
    id: string
    name: string
    slug?: string
    status: 'processing' | 'wiki_generated' | 'failed' | 'no_documents'
    documentCount: number
    createdAt: string
    lastUpdated?: string
  }
  className?: string
  onDelete?: () => void // Callback to refresh the project list after deletion
}

export function ProjectCard({ project, className, onDelete }: ProjectCardProps) {
  const router = useRouter()
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const getStatusIcon = () => {
    switch (project.status) {
      case 'wiki_generated':
        return <CheckCircle className="h-4 w-4 text-primary" />
      case 'processing':
        return <Clock className="h-4 w-4 text-muted-foreground" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-destructive" />
      case 'no_documents':
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getStatusText = () => {
    switch (project.status) {
      case 'wiki_generated':
        return 'Wiki Generated'
      case 'processing':
        return 'Processing'
      case 'failed':
        return 'Processing Failed'
      case 'no_documents':
        return 'No Documents'
      default:
        return 'Unknown'
    }
  }

  const getStatusBadgeVariant = () => {
    switch (project.status) {
      case 'wiki_generated':
        return 'default'
      case 'processing':
        return 'secondary'
      case 'failed':
        return 'destructive'
      case 'no_documents':
        return 'outline'
      default:
        return 'outline'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  // Generate project URL using dashboard routes: /dashboard/projects/{projectSlug}/{runId}
  const projectUrl = project.slug 
    ? `/dashboard/projects/${project.slug}` 
    : `/dashboard/projects/project-${project.id}`

  // Make all projects with wikis clickable
  const isClickable = project.status === 'wiki_generated'

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault() // Prevent navigation if card is clickable
    e.stopPropagation() // Prevent event bubbling
    setShowDeleteDialog(true)
  }

  const confirmDelete = async () => {
    setIsDeleting(true)
    try {
      const result = await apiClient.deleteProject(project.id)
      if (result.success || result.message) {
        toast.success(result.message || "Project has been moved to trash and can be recovered within 30 days.")
        // Call the onDelete callback to refresh the list
        if (onDelete) {
          onDelete()
        }
        // Optionally refresh the page
        router.refresh()
      } else {
        throw new Error("Failed to delete project")
      }
    } catch (error) {
      console.error('Delete error:', error)
      toast.error(error instanceof Error ? error.message : "Failed to delete project")
    } finally {
      setIsDeleting(false)
      setShowDeleteDialog(false)
    }
  }

  const CardWrapper = isClickable ? Link : 'div'
  const wrapperProps = isClickable ? { href: projectUrl } : {}

  return (
    <>
      <CardWrapper {...wrapperProps}>
      <Card className={cn(
        "bg-card border-border transition-all duration-200",
        isClickable && "hover:bg-secondary/50 cursor-pointer hover:border-primary/50",
        !isClickable && "opacity-75",
        className
      )}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <FolderOpen className="h-5 w-5 text-primary flex-shrink-0" />
              <h3 className="font-semibold text-foreground truncate">
                {project.name}
              </h3>
            </div>
            <div className="flex items-center gap-1 ml-2">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-destructive"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              {getStatusIcon()}
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="pt-0">
          <div className="space-y-3">
            {/* Document count */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span>
                {project.documentCount} Document{project.documentCount !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Status badge */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">Status</span>
              <Badge 
                variant={getStatusBadgeVariant()}
                className="flex items-center gap-1"
              >
                {getStatusIcon()}
                {getStatusText()}
              </Badge>
            </div>

            {/* Date info */}
            <div className="text-xs text-muted-foreground pt-2 border-t border-border">
              <div>Created {formatDate(project.createdAt)}</div>
              {project.lastUpdated && (
                <div>Updated {formatDate(project.lastUpdated)}</div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </CardWrapper>

    <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Project</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete "{project.name}"? 
            This action will move the project to trash where it can be recovered within 30 days.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirmDelete}
            disabled={isDeleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  )
}