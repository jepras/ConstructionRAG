"use client"

import Link from "next/link"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { FileText, CheckCircle, Clock, AlertCircle, FolderOpen } from "lucide-react"
import { cn } from "@/lib/utils"

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
}

export function ProjectCard({ project, className }: ProjectCardProps) {
  const getStatusIcon = () => {
    switch (project.status) {
      case 'wiki_generated':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      case 'no_documents':
        return <AlertCircle className="h-4 w-4 text-gray-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
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

  // Generate project URL based on status and slug
  const projectUrl = project.slug && project.status === 'wiki_generated' 
    ? `/projects/${project.slug}` 
    : `/dashboard/projects/${project.id}`

  const isClickable = project.status === 'wiki_generated' || project.documentCount > 0

  const CardWrapper = isClickable ? Link : 'div'
  const wrapperProps = isClickable ? { href: projectUrl } : {}

  return (
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
  )
}