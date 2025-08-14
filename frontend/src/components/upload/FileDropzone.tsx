"use client"

import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, X, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void
  selectedFiles: File[]
  onRemoveFile: (index: number) => void
  maxFiles?: number
  maxSize?: number
  disabled?: boolean
}

export function FileDropzone({
  onFilesSelected,
  selectedFiles,
  onRemoveFile,
  maxFiles = 5,
  maxSize = 50 * 1024 * 1024, // 50MB
  disabled = false
}: FileDropzoneProps) {
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError(null)

    if (rejectedFiles.length > 0) {
      const errors = rejectedFiles.map(({ errors }) => 
        errors.map((e: any) => e.message).join(", ")
      ).join("; ")
      setError(errors)
      return
    }

    const totalFiles = selectedFiles.length + acceptedFiles.length
    if (totalFiles > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed`)
      return
    }

    onFilesSelected([...selectedFiles, ...acceptedFiles])
  }, [selectedFiles, onFilesSelected, maxFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize,
    disabled: disabled || selectedFiles.length >= maxFiles,
    multiple: true
  })

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all",
          "hover:border-primary hover:bg-card/50",
          isDragActive && "border-primary bg-card/50",
          disabled && "opacity-50 cursor-not-allowed",
          selectedFiles.length >= maxFiles && "opacity-50 cursor-not-allowed",
          "border-border bg-card"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
        {isDragActive ? (
          <p className="text-foreground">Drop the files here...</p>
        ) : (
          <>
            <p className="text-foreground mb-2">
              Click to upload or drag and drop
            </p>
            <p className="text-sm text-muted-foreground">
              PDF files only • Maximum {maxFiles} files • Up to {formatFileSize(maxSize)} each
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">
            Selected files ({selectedFiles.length}/{maxFiles})
          </p>
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-card border border-border rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onRemoveFile(index)}
                  disabled={disabled}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}