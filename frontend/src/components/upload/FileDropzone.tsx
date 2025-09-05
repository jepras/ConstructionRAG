"use client"

import { useCallback, useState, useEffect } from "react"
import { useDropzone } from "react-dropzone"
import { Upload, X, FileText, CheckCircle, AlertCircle, Clock, Loader2, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"
import { useFileValidation } from "@/hooks/useFileValidation"

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void
  selectedFiles: File[]
  onRemoveFile: (index: number) => void
  onValidationComplete?: (isValid: boolean, estimatedMinutes: number) => void
  onValidationErrors?: (hasErrors: boolean) => void
  maxFiles?: number
  maxSize?: number
  disabled?: boolean
  showValidation?: boolean
}

export function FileDropzone({
  onFilesSelected,
  selectedFiles,
  onRemoveFile,
  onValidationComplete,
  onValidationErrors,
  maxFiles = 5,
  maxSize = 50 * 1024 * 1024, // 50MB
  disabled = false,
  showValidation = true
}: FileDropzoneProps) {
  const [error, setError] = useState<string | null>(null)
  
  const {
    validateFiles,
    clearValidation,
    getFileValidation,
    isValidating,
    overallValid,
    totalPages,
    estimatedMinutes,
    errors: validationErrors,
    warnings: validationWarnings
  } = useFileValidation()

  // Track if component has mounted to avoid validation on initial render
  const [hasMounted, setHasMounted] = useState(false)
  
  useEffect(() => {
    setHasMounted(true)
  }, [])

  // Trigger validation when files change (but not on mount)
  useEffect(() => {
    if (!hasMounted) return
    
    if (showValidation && selectedFiles.length > 0) {
      validateFiles(selectedFiles)
    } else if (selectedFiles.length === 0) {
      clearValidation()
    }
    // Remove validateFiles and clearValidation from deps to avoid infinite loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFiles, showValidation, hasMounted])

  // Notify parent when validation completes
  useEffect(() => {
    if (onValidationComplete && !isValidating && selectedFiles.length > 0) {
      onValidationComplete(overallValid, estimatedMinutes)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isValidating, overallValid, estimatedMinutes, selectedFiles.length])

  // Notify parent about validation errors (not warnings)
  useEffect(() => {
    if (onValidationErrors && !isValidating && selectedFiles.length > 0) {
      onValidationErrors(validationErrors.length > 0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isValidating, validationErrors.length, selectedFiles.length])

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
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all relative overflow-hidden",
          "hover:border-primary hover:bg-card/50",
          isDragActive && "border-primary bg-card/50",
          disabled && "opacity-50 cursor-not-allowed",
          selectedFiles.length >= maxFiles && "opacity-50 cursor-not-allowed",
          "border-border bg-card"
        )}
      >
        <input {...getInputProps()} />
        
        {/* Background document icons */}
        <div className="absolute inset-0 flex items-center justify-center opacity-20">
          <div className="relative w-full h-full flex items-center justify-center">
            {/* Left document - blue */}
            <div className="absolute -left-4 -top-2 transform -rotate-12">
              <svg width="48" height="56" viewBox="0 0 24 28" fill="none" className="text-blue-400">
                <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
                <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
                <path d="M8 12H16M8 16H12" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
            </div>
            
            {/* Center-left document - green */}
            <div className="absolute -left-2 top-0 transform rotate-6">
              <svg width="48" height="56" viewBox="0 0 24 28" fill="none" className="text-green-500">
                <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.4"/>
                <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
                <rect x="8" y="12" width="8" height="1.5" fill="currentColor"/>
                <rect x="8" y="15" width="6" height="1.5" fill="currentColor"/>
                <rect x="8" y="18" width="8" height="1.5" fill="currentColor"/>
              </svg>
            </div>
            
            {/* Center-right document - gray */}
            <div className="absolute right-2 -top-1 transform -rotate-8">
              <svg width="48" height="56" viewBox="0 0 24 28" fill="none" className="text-gray-400">
                <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
                <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
                <path d="M8 12H16M8 16H14M8 20H12" stroke="currentColor" strokeWidth="1.5"/>
              </svg>
            </div>
            
            {/* Right document - red */}
            <div className="absolute right-0 top-2 transform rotate-15">
              <svg width="48" height="56" viewBox="0 0 24 28" fill="none" className="text-red-400">
                <path d="M14 2L20 8V26H4V2H14Z" stroke="currentColor" strokeWidth="2" fill="currentColor" fillOpacity="0.3"/>
                <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" fill="none"/>
                <circle cx="12" cy="16" r="3" stroke="currentColor" strokeWidth="1.5" fill="none"/>
              </svg>
            </div>
          </div>
        </div>
        
        {/* Central upload icon */}
        <div className="relative z-10 flex flex-col items-center">
          <div className="bg-background/90 backdrop-blur-sm rounded-full p-4 mb-4 border border-border/50">
            <Upload className="h-8 w-8 text-foreground" />
          </div>
          
          {isDragActive ? (
            <p className="text-foreground font-medium">Drop the files here...</p>
          ) : (
            <>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Drag & Drop Your Project
              </h3>
              <p className="text-foreground mb-2">
                Click to upload or drag and drop
              </p>
              <p className="text-sm text-muted-foreground">
                PDF files only • Maximum {maxFiles} files • Up to {formatFileSize(maxSize)} each
              </p>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">
              Selected files ({selectedFiles.length}/{maxFiles})
            </p>
            {showValidation && isValidating && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Validating...
              </div>
            )}
            {showValidation && !isValidating && selectedFiles.length > 0 && (
              <div className="flex items-center gap-2 text-sm">
                {overallValid ? (
                  <HoverCard>
                    <HoverCardTrigger asChild>
                      <div className="flex items-center gap-2 cursor-help">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-green-600 border-b border-dotted border-green-600">
                          {totalPages} pages • ~{estimatedMinutes} min
                        </span>
                        <Info className="h-3 w-3 text-green-600" />
                      </div>
                    </HoverCardTrigger>
                    <HoverCardContent className="w-80">
                      <div className="space-y-2">
                        <h4 className="text-sm font-semibold">Processing Time Estimate</h4>
                        <p className="text-sm text-muted-foreground">
                          These are rough estimates that depend on PDF complexity. 
                          We use pessimistic calculations assuming worst-case scenarios 
                          (OCR processing, complex tables, image extraction) to avoid 
                          underestimating.
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Actual processing may be faster.
                        </p>
                      </div>
                    </HoverCardContent>
                  </HoverCard>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <span className="text-destructive">Validation failed</span>
                  </>
                )}
              </div>
            )}
          </div>
          <div className="space-y-2">
            {selectedFiles.map((file, index) => {
              const validation = showValidation ? getFileValidation(file.name) : undefined
              const isValid = validation ? validation.is_valid : true
              const pageCount = validation?.metadata?.page_count
              const processingTime = validation?.processing_estimate?.estimated_minutes
              
              return (
                <div
                  key={index}
                  className={cn(
                    "flex items-center justify-between p-3 bg-card border rounded-lg",
                    showValidation && validation && !isValid
                      ? "border-destructive/50 bg-destructive/5"
                      : "border-border"
                  )}
                >
                  <div className="flex items-center space-x-3">
                    {showValidation && validation ? (
                      isValid ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <AlertCircle className="h-5 w-5 text-destructive" />
                      )
                    ) : (
                      <FileText className="h-5 w-5 text-muted-foreground" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-foreground">{file.name}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{formatFileSize(file.size)}</span>
                        {showValidation && validation && (
                          <>
                            {pageCount && (
                              <span className="flex items-center gap-1">
                                <FileText className="h-3 w-3" />
                                {pageCount} pages
                              </span>
                            )}
                            {processingTime && (
                              <HoverCard>
                                <HoverCardTrigger asChild>
                                  <span className="flex items-center gap-1 cursor-help border-b border-dotted border-muted-foreground">
                                    <Clock className="h-3 w-3" />
                                    ~{processingTime} min
                                  </span>
                                </HoverCardTrigger>
                                <HoverCardContent>
                                  <p className="text-xs">Estimated processing time (pessimistic calculation)</p>
                                </HoverCardContent>
                              </HoverCard>
                            )}
                          </>
                        )}
                      </div>
                      {showValidation && validation && !isValid && validation.errors.length > 0 && (
                        <p className="text-xs text-destructive mt-1">
                          {validation.errors[0]}
                        </p>
                      )}
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
              )
            })}
          </div>
          
          {showValidation && validationErrors.length > 0 && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3">
              <p className="text-sm font-medium text-destructive mb-1">Validation Errors:</p>
              <ul className="text-xs text-destructive space-y-1">
                {validationErrors.map((error, i) => (
                  <li key={i}>• {error}</li>
                ))}
              </ul>
            </div>
          )}
          
          {showValidation && validationWarnings.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
              <p className="text-sm font-medium text-yellow-700 mb-1">Warnings:</p>
              <ul className="text-xs text-yellow-600 space-y-1">
                {validationWarnings.map((warning, i) => (
                  <li key={i}>• {warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}