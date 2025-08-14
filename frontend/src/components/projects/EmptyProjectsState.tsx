"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { FolderOpen, Plus } from "lucide-react"

export function EmptyProjectsState() {
  return (
    <Card className="bg-card border-border border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-6">
          <FolderOpen className="h-16 w-16 text-muted-foreground/50" />
        </div>
        
        <h3 className="text-xl font-semibold text-foreground mb-2">
          No projects yet
        </h3>
        
        <p className="text-muted-foreground mb-8 max-w-md">
          Get started by creating your first construction project. Upload your documents 
          and let our AI generate a comprehensive project wiki.
        </p>
        
        <Link href="/dashboard/new-project">
          <Button size="lg" className="gap-2">
            <Plus className="h-4 w-4" />
            Create Your First Project
          </Button>
        </Link>
      </CardContent>
    </Card>
  )
}