import { useState, useCallback, useRef } from "react"
import { useMutation } from "@tanstack/react-query"

interface FileValidationResult {
  filename: string
  is_valid: boolean
  errors: string[]
  warnings: string[]
  metadata: {
    file_size_bytes: number
    file_size_mb: number
    file_hash: string
    page_count?: number
    pdf_version?: string
  }
  page_analysis: {
    total_pages?: number
    estimated_text_pages?: number
    estimated_complex_pages?: number
    estimated_scanned_pages?: number
    avg_text_per_page?: number
    is_likely_scanned?: boolean
  }
  security: {
    has_javascript: boolean
    has_embedded_files: boolean
    has_external_links: boolean
    suspicious_patterns: string[]
  }
  processing_estimate: {
    estimated_seconds: number
    estimated_minutes: number
    confidence: "low" | "medium" | "high"
    breakdown?: {
      text_pages_time: number
      complex_pages_time: number
      scanned_pages_time: number
      overhead_time: number
    }
  }
}

interface ValidationResponse {
  files: FileValidationResult[]
  is_valid: boolean
  total_pages: number
  total_processing_time_estimate: number
  total_processing_time_minutes: number
  errors: string[]
  warnings: string[]
}

interface ValidationState {
  isValidating: boolean
  validationResults: Map<string, FileValidationResult>
  overallValid: boolean
  totalPages: number
  estimatedMinutes: number
  errors: string[]
  warnings: string[]
}

export function useFileValidation() {
  const [validationState, setValidationState] = useState<ValidationState>({
    isValidating: false,
    validationResults: new Map(),
    overallValid: true,
    totalPages: 0,
    estimatedMinutes: 0,
    errors: [],
    warnings: [],
  })

  // Cache validation results by file hash
  const validationCache = useRef<Map<string, FileValidationResult>>(new Map())

  const validateMutation = useMutation<ValidationResponse, Error, File[]>({
    mutationFn: async (files: File[]) => {
      // Create FormData with files
      const formData = new FormData()
      files.forEach(file => {
        formData.append("files", file)
      })

      // Get the base URL from environment or use default
      const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      // Call validation endpoint directly using fetch
      const response = await fetch(`${baseURL}/api/uploads/validate`, {
        method: 'POST',
        body: formData,
        credentials: 'include', // Include cookies for authentication
      })

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('Rate limit exceeded. Please wait before validating more files.')
        }
        throw new Error(`Validation failed: ${response.statusText}`)
      }

      return await response.json()
    },
    onMutate: () => {
      setValidationState(prev => ({
        ...prev,
        isValidating: true,
        errors: [],
        warnings: [],
      }))
    },
    onSuccess: (data) => {
      // Update validation state with results
      const resultsMap = new Map<string, FileValidationResult>()
      
      data.files.forEach(file => {
        resultsMap.set(file.filename, file)
        // Cache by hash if available
        if (file.metadata?.file_hash) {
          validationCache.current.set(file.metadata.file_hash, file)
        }
      })

      setValidationState({
        isValidating: false,
        validationResults: resultsMap,
        overallValid: data.is_valid,
        totalPages: data.total_pages,
        estimatedMinutes: data.total_processing_time_minutes,
        errors: data.errors,
        warnings: data.warnings,
      })
    },
    onError: (error) => {
      console.error("Validation error:", error)
      
      // Handle rate limiting
      if (error.message?.includes("429") || error.message?.includes("Rate limit")) {
        setValidationState(prev => ({
          ...prev,
          isValidating: false,
          overallValid: false,
          errors: ["Rate limit exceeded. Please wait before validating more files."],
        }))
      } else {
        setValidationState(prev => ({
          ...prev,
          isValidating: false,
          overallValid: false,
          errors: [error.message || "Failed to validate files"],
        }))
      }
    },
  })

  const validateFiles = useCallback(async (files: File[]) => {
    if (files.length === 0) {
      setValidationState({
        isValidating: false,
        validationResults: new Map(),
        overallValid: true,
        totalPages: 0,
        estimatedMinutes: 0,
        errors: [],
        warnings: [],
      })
      return
    }

    // Check cache for already validated files
    const uncachedFiles: File[] = []
    const cachedResults: FileValidationResult[] = []

    for (const file of files) {
      // Simple hash check by name and size (not perfect but fast)
      const simpleHash = `${file.name}-${file.size}`
      const cached = validationCache.current.get(simpleHash)
      
      if (cached) {
        cachedResults.push(cached)
      } else {
        uncachedFiles.push(file)
      }
    }

    // If all files are cached, use cached results
    if (uncachedFiles.length === 0 && cachedResults.length > 0) {
      const resultsMap = new Map<string, FileValidationResult>()
      let totalPages = 0
      let totalSeconds = 0
      let overallValid = true
      const errors: string[] = []
      const warnings: string[] = []

      cachedResults.forEach(result => {
        resultsMap.set(result.filename, result)
        if (!result.is_valid) overallValid = false
        if (result.metadata?.page_count) totalPages += result.metadata.page_count
        if (result.processing_estimate?.estimated_seconds) {
          totalSeconds += result.processing_estimate.estimated_seconds
        }
        errors.push(...result.errors.map(e => `${result.filename}: ${e}`))
        warnings.push(...result.warnings.map(w => `${result.filename}: ${w}`))
      })

      setValidationState({
        isValidating: false,
        validationResults: resultsMap,
        overallValid,
        totalPages,
        estimatedMinutes: Math.round(totalSeconds / 60 * 10) / 10,
        errors,
        warnings,
      })
      return
    }

    // Validate uncached files
    validateMutation.mutate(files)
  }, []) // Remove validateMutation from deps since it's stable

  const clearValidation = useCallback(() => {
    setValidationState({
      isValidating: false,
      validationResults: new Map(),
      overallValid: true,
      totalPages: 0,
      estimatedMinutes: 0,
      errors: [],
      warnings: [],
    })
  }, [])

  const getFileValidation = useCallback((filename: string): FileValidationResult | undefined => {
    return validationState.validationResults.get(filename)
  }, [validationState.validationResults])

  return {
    validateFiles,
    clearValidation,
    getFileValidation,
    isValidating: validationState.isValidating || validateMutation.isPending,
    validationResults: validationState.validationResults,
    overallValid: validationState.overallValid,
    totalPages: validationState.totalPages,
    estimatedMinutes: validationState.estimatedMinutes,
    errors: validationState.errors,
    warnings: validationState.warnings,
  }
}