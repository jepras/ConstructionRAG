import { createClient } from './supabase'

export interface ApiResponse<T> {
  data?: T
  error?: string
  status: number
}

export interface AuthResponse {
  success: boolean
  message: string
  access_token?: string
  refresh_token?: string
  user_id?: string
  email?: string
  expires_at?: string
}

export interface User {
  id: string
  email: string
  profile?: {
    id: string
    email: string
    full_name?: string
    created_at: string
    updated_at: string
  }
}

// Wiki-related interfaces
export interface WikiPage {
  filename: string
  title: string
  size: number
  storage_path: string
  storage_url: string
  order: number
  name?: string // Added for frontend compatibility (filename without .md)
  sections?: WikiSection[]
}

export interface WikiSection {
  title: string
  level: number
  id: string
}

export interface WikiPageContent {
  name: string
  title: string
  content: string
  metadata?: {
    word_count: number
    last_updated: string
  }
}

export interface WikiMetadata {
  wiki_run_id: string
  metadata: {
    wiki_structure?: {
      title?: string
      description?: string
      pages?: Array<{
        id: string
        title: string
        description: string
        queries: string[]
        relevance_score: string
      }>
    }
    pages_metadata?: Array<{
      title: string
      filename: string
      storage_path: string
      storage_url: string
      file_size: number
      order: number
    }>
  }
}

export interface WikiRunStatus {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: {
    current_step: string
    steps_completed: number
    total_steps: number
  }
}

export interface WikiRun {
  id: string
  indexing_run_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
}

export interface WikiInitialData {
  indexing_run_id: string
  wiki_run: WikiRun | null
  pages: WikiPage[]
  total_pages: number
  first_page_content: WikiPageContent | null
  metadata: WikiMetadata | null
  message?: string
}

// Checklist Analysis interfaces
export interface ChecklistAnalysisRequest {
  indexing_run_id: string
  checklist_content: string
  checklist_name: string
  model_name?: string
}

export interface ChecklistAnalysisResponse {
  analysis_run_id: string
  status: string
  message: string
}

export interface ChecklistSourceReference {
  document: string
  page: number
  excerpt?: string
}

export interface ChecklistResult {
  id: string
  item_number: string
  item_name: string
  status: 'found' | 'missing' | 'risk' | 'conditions' | 'pending_clarification'
  description: string
  confidence_score?: number
  source_document?: string
  source_page?: number
  source_excerpt?: string
  all_sources?: ChecklistSourceReference[]
  created_at?: string
}

export interface ChecklistAnalysisRun {
  id: string
  indexing_run_id: string
  user_id?: string
  checklist_name: string
  checklist_content: string
  model_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  raw_output?: string
  progress_current: number
  progress_total: number
  error_message?: string
  access_level: string
  results?: ChecklistResult[]
  created_at: string
  updated_at: string
}

// Pipeline Configuration interfaces (matching actual API structure)
export interface PipelineConfig {
  storage?: {
    collection_prefix: string
    validation_sample_size: number
  }
  chunking?: {
    overlap: number
    strategy: string
    chunk_size: number
    separators: string[]
    max_chunk_size: number
    min_chunk_size: number
  }
  metadata?: {
    detect_sections: boolean
    preserve_formatting: boolean
    extract_page_structure: boolean
  }
  embedding?: {
    model: string
    provider: string
    batch_size: number
    dimensions: number
    max_retries: number
    retry_delay: number
    timeout_seconds?: number
    cost_tracking?: boolean
    resume_capability?: boolean
  }
  partition?: {
    hybrid_mode: boolean
    ocr_strategy: string
    ocr_languages: string[]
    extract_images: boolean
    extract_tables: boolean
    max_image_size_mb: number
    scanned_detection: {
      sample_pages: number
      text_threshold: number
    }
  }
  enrichment?: {
    merge_related_elements?: boolean
    min_content_length?: number
  }
  generation?: {
    model: string
    max_tokens: number
    temperature: number
  }
  retrieval?: {
    method?: string
    top_k?: number
    similarity_threshold?: number
    similarity_metric?: string
  }
  orchestration?: {
    max_concurrent_documents?: number
    step_timeout_minutes?: number
    retry_attempts?: number
    fail_fast?: boolean
  }
}

export interface IndexingRunDocument {
  id: string
  filename: string
  file_size: number
  file_type?: string
  upload_path?: string
  created_at: string
  upload_type: string
}

export interface IndexingRunWithConfig {
  id: string
  name: string
  status: string
  created_at: string
  completed_at?: string
  upload_type: 'email' | 'user_project'
  access_level: 'public' | 'auth' | 'owner' | 'private'
  pipeline_config?: PipelineConfig
  documents?: IndexingRunDocument[]
}

export interface ProjectDetails {
  id: string
  name: string
  description: string
  status: string
  created_at: string
  upload_type: 'email' | 'user_project'
  access_level: 'public' | 'auth' | 'owner' | 'private'
  stats?: {
    documents: number
    wikiPages: number
    totalSize: string
  }
  wiki_run_id?: string
}

// Query-related interfaces
export interface CreateQueryRequest {
  query: string
  indexing_run_id?: string
}

export interface SearchResult {
  content: string
  metadata: {
    document_id: string
    filename: string
    page_number?: number
    section_title?: string
    bbox?: number[]
    [key: string]: any
  }
  similarity_score: number
  source_filename: string
  page_number?: number
  chunk_id: string
  bbox?: number[]
  document_id?: string
}

export interface QueryResponse {
  id?: string
  query: string
  response: string
  search_results: SearchResult[]
  performance_metrics?: {
    total_time: number
    steps: Record<string, number>
    model_used?: string
  }
  quality_metrics?: {
    relevance_score?: number
    confidence?: number
  }
  step_timings?: Record<string, number>
  created_at?: string
}

export interface QueryHistoryItem {
  id: string
  query: string
  response: string
  indexing_run_id: string
  created_at: string
}

export class ApiClient {
  private baseURL: string
  private authCache: {
    token: string | null
    expiresAt: number
  } = {
    token: null,
    expiresAt: 0
  }

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL!
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const now = Date.now()
    
    // Use cached token if it's still valid (with 5-minute buffer)
    if (this.authCache.token && this.authCache.expiresAt > now + 5 * 60 * 1000) {
      return { Authorization: `Bearer ${this.authCache.token}` }
    }

    try {
      const supabase = createClient()
      const { data: { session }, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Error getting auth session:', error)
        this.authCache = { token: null, expiresAt: 0 }
        return {}
      }

      if (session?.access_token) {
        // Cache the token with its expiration time
        this.authCache = {
          token: session.access_token,
          expiresAt: (session.expires_at || 0) * 1000 // Convert to milliseconds
        }
        return { Authorization: `Bearer ${session.access_token}` }
      }

      // No session, clear cache
      this.authCache = { token: null, expiresAt: 0 }
      return {}
    } catch (error) {
      console.error('Error in getAuthHeaders:', error)
      this.authCache = { token: null, expiresAt: 0 }
      return {}
    }
  }

  // Method to clear auth cache when auth state changes
  public clearAuthCache(): void {
    this.authCache = { token: null, expiresAt: 0 }
  }

  private async request<T>(
    endpoint: string, 
    options?: RequestInit & { 
      params?: Record<string, unknown>
      next?: { 
        revalidate?: number | false
        tags?: string[] 
      }
    }
  ): Promise<T> {
    const url = new URL(endpoint, this.baseURL)
    
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }

    // Add Next.js fetch caching
    const fetchOptions: RequestInit & { next?: any } = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    }

    // Only add Next.js caching for GET requests in static generation contexts
    if ((!options?.method || options.method === 'GET') && options?.next && typeof options.next === 'object') {
      fetchOptions.next = {
        revalidate: options.next.revalidate !== undefined ? options.next.revalidate : 3600,
        tags: options.next.tags || [`api-${endpoint.replace(/\//g, '-')}`],
      }
    }

    const response = await fetch(url.toString(), fetchOptions)

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API Error ${response.status}: ${errorText}`)
    }

    return response.json()
  }

  // Auth methods
  async signUp(email: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async signIn(email: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/signin', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async signOut(): Promise<AuthResponse> {
    const headers = await this.getAuthHeaders()
    return this.request<AuthResponse>('/api/auth/signout', {
      method: 'POST',
      headers,
    })
  }

  async getCurrentUser(): Promise<User> {
    const headers = await this.getAuthHeaders()
    return this.request<User>('/api/auth/me', {
      headers,
    })
  }

  async refreshToken(refreshToken: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  }

  async resetPassword(email: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  async updateUserProfile(updates: { full_name?: string; email?: string }): Promise<any> {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    
    if (!user) {
      throw new Error('Not authenticated')
    }

    // Use upsert to handle both update and insert cases
    const { data, error } = await supabase
      .from('user_profiles')
      .upsert({
        id: user.id,
        email: user.email,
        ...updates,
      })
      .select()
      .single()

    if (error) {
      throw new Error(`Failed to update profile: ${error.message}`)
    }

    return data
  }

  // Public Projects methods
  async getPublicProjects(limit: number = 50, offset: number = 0): Promise<any[]> {
    // Fetch indexing runs that are public (email uploads)
    // No auth headers needed for anonymous access to public runs
    return this.request<any[]>('/api/indexing-runs', {
      params: {
        limit,
        offset,
      }
    })
  }

  async getProjectWikiStatus(indexingRunId: string): Promise<any> {
    // Check if a wiki generation exists for an indexing run
    return this.request<any>(`/api/wiki/runs/${indexingRunId}`, {
      // No auth required for public wikis
    })
  }

  async getPublicProjectsWithWikis(limit: number = 50): Promise<any[]> {
    return this.request<any[]>(`/api/indexing-runs-with-wikis?limit=${limit}`, {
      next: {
        revalidate: 1800, // 30 minutes cache for project list
        tags: ['public-projects-with-wikis']
      }
    });
  }

  // File upload methods
  async uploadFiles(formData: FormData): Promise<any> {
    const response = await fetch(`${this.baseURL}/api/uploads`, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - let browser set it with boundary for multipart/form-data
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Upload failed: ${errorText}`)
    }

    return response.json()
  }

  async getIndexingProgress(indexingRunId: string): Promise<any> {
    return this.request<any>(`/api/indexing-runs/${indexingRunId}/progress`)
  }

  async getIndexingRun(indexingRunId: string): Promise<any> {
    return this.request<any>(`/api/indexing-runs/${indexingRunId}`)
  }

  // Wiki-related methods
  async getWikiPages(wikiRunId: string): Promise<{pages: WikiPage[], total_pages: number}> {
    const headers = await this.getAuthHeaders()
    return this.request<{pages: WikiPage[], total_pages: number}>(`/api/wiki/runs/${wikiRunId}/pages`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for wiki pages list
        tags: [`wiki-pages-${wikiRunId}`, 'wiki-pages']
      }
    })
  }

  async getWikiPageContent(wikiRunId: string, pageName: string): Promise<WikiPageContent> {
    const headers = await this.getAuthHeaders()
    return this.request<WikiPageContent>(`/api/wiki/runs/${wikiRunId}/pages/${pageName}`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for wiki page content
        tags: [`wiki-content-${wikiRunId}-${pageName}`, 'wiki-content']
      }
    })
  }

  async getWikiMetadata(wikiRunId: string): Promise<WikiMetadata> {
    const headers = await this.getAuthHeaders()
    return this.request<WikiMetadata>(`/api/wiki/runs/${wikiRunId}/metadata`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for wiki metadata
        tags: [`wiki-metadata-${wikiRunId}`, 'wiki-metadata']
      }
    })
  }

  async getWikiRunStatus(wikiRunId: string): Promise<WikiRunStatus> {
    const headers = await this.getAuthHeaders()
    return this.request<WikiRunStatus>(`/api/wiki/runs/${wikiRunId}/status`, {
      headers
    })
  }

  async getWikiRunsByIndexingRun(indexingRunId: string): Promise<WikiRun[]> {
    const headers = await this.getAuthHeaders()
    return this.request<WikiRun[]>(`/api/wiki/runs/${indexingRunId}`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for wiki runs
        tags: [`wiki-runs-${indexingRunId}`, 'wiki-runs']
      }
    })
  }

  async getWikiInitialData(indexingRunId: string): Promise<WikiInitialData> {
    const headers = await this.getAuthHeaders()
    return this.request<WikiInitialData>(`/api/wiki/initial/${indexingRunId}`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for wiki initial data
        tags: [`wiki-initial-${indexingRunId}`, 'wiki-initial']
      }
    })
  }

  // Project-related methods
  // Legacy methods removed - use getProjectWithRun() and getProjectRuns() instead

  async deleteIndexingRun(indexingRunId: string): Promise<{ success: boolean; message: string }> {
    const headers = await this.getAuthHeaders()
    return this.request<{ success: boolean; message: string }>(`/api/indexing-runs/${indexingRunId}`, {
      method: 'DELETE',
      headers,
    })
  }

  async getIndexingRunDocuments(indexingRunId: string): Promise<IndexingRunDocument[]> {
    const response = await this.request<{ documents: IndexingRunDocument[] }>(`/api/documents`, {
      params: { index_run_id: indexingRunId },
      next: {
        revalidate: 3600, // 1 hour cache for documents
        tags: [`documents-${indexingRunId}`, 'documents']
      }
    })
    return response.documents || []
  }

  // Project management methods for authenticated users
  async createProject(projectData: {
    name: string
    initial_version_name?: string
    visibility: 'public' | 'private'
    share_with_ai: boolean
    language: string
    expert_modules?: string[]
    files: File[]
  }): Promise<{ project_id: string; id: string }> {
    const headers = await this.getAuthHeaders()
    
    // First create the project with metadata
    const projectPayload = {
      name: projectData.name,
      initial_version_name: projectData.initial_version_name || 'Initial Version',
      visibility: projectData.visibility,
      share_with_ai: projectData.share_with_ai,
      language: projectData.language,
      expert_modules: projectData.expert_modules || []
    }

    const projectResponse = await fetch(`${this.baseURL}/api/projects`, {
      method: 'POST',
      body: JSON.stringify(projectPayload),
      headers: {
        ...headers,
        'Content-Type': 'application/json',
      }
    })

    if (!projectResponse.ok) {
      const errorText = await projectResponse.text()
      throw new Error(`Project creation failed: ${errorText}`)
    }

    const project = await projectResponse.json()

    // If there are files, upload them to the project
    if (projectData.files.length > 0) {
      const formData = new FormData()
      projectData.files.forEach(file => {
        formData.append('files', file)
      })
      formData.append('upload_type', 'user_project')
      formData.append('project_id', project.project_id || project.id)

      const uploadResponse = await fetch(`${this.baseURL}/api/uploads`, {
        method: 'POST',
        body: formData,
        headers: {
          ...headers,
          // Don't set Content-Type for FormData
        }
      })

      if (!uploadResponse.ok) {
        const errorText = await uploadResponse.text()
        // Project was created but file upload failed
        console.error(`File upload failed for project ${project.id}: ${errorText}`)
        // Could delete the project here if needed, but for now just log the error
      }
    }

    return project
  }

  async getUserProjects(limit: number = 50, offset: number = 0): Promise<any[]> {
    const headers = await this.getAuthHeaders()
    return this.request<any[]>('/api/projects', {
      headers,
      params: {
        limit,
        offset,
      }
    })
  }

  async getUserProjectsWithWikis(limit: number = 50, offset: number = 0): Promise<any[]> {
    const headers = await this.getAuthHeaders()
    return this.request<any[]>('/api/user-projects-with-wikis', {
      headers,
      params: {
        limit,
        offset,
      },
      next: {
        revalidate: 300, // 5 minutes cache for user projects with wikis
        tags: ['user-projects-with-wikis']
      }
    })
  }

  async getProject(projectId: string): Promise<any> {
    const headers = await this.getAuthHeaders()
    return this.request<any>(`/api/projects/${projectId}`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for project details
        tags: [`project-${projectId}`, 'projects']
      }
    })
  }

  async updateProject(projectId: string, updates: {
    name?: string
    visibility?: 'public' | 'private'
    description?: string
  }): Promise<any> {
    const headers = await this.getAuthHeaders()
    return this.request<any>(`/api/projects/${projectId}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(updates),
    })
  }

  async deleteProject(projectId: string): Promise<{ success: boolean; message: string }> {
    const headers = await this.getAuthHeaders()
    return this.request<{ success: boolean; message: string }>(`/api/projects/${projectId}`, {
      method: 'DELETE',
      headers,
    })
  }

  // New unified endpoints for nested route structure
  async getProjectWithRun(projectId: string, runId: string): Promise<any> {
    const headers = await this.getAuthHeaders()
    return this.request<any>(`/api/projects/${projectId}/runs/${runId}`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for project with run data
        tags: [`project-${projectId}`, `run-${runId}`, 'projects', 'runs']
      }
    })
  }

  async getProjectRuns(projectId: string): Promise<any[]> {
    const headers = await this.getAuthHeaders()
    return this.request<any[]>(`/api/projects/${projectId}/runs`, {
      headers,
      next: {
        revalidate: 300, // 5 minutes cache for project runs
        tags: [`project-runs-${projectId}`, 'projects', 'runs']
      }
    })
  }

  // Query methods
  async createQuery(request: CreateQueryRequest): Promise<QueryResponse> {
    // Try to get auth headers, but don't fail if not authenticated (public projects)
    let headers = {}
    try {
      headers = await this.getAuthHeaders()
    } catch {
      // Continue without auth headers for public projects
    }
    
    return this.request<QueryResponse>('/api/queries', {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    })
  }

  async getQueries(limit: number = 50, offset: number = 0): Promise<QueryHistoryItem[]> {
    // Try to get auth headers, but don't fail if not authenticated
    let headers = {}
    try {
      headers = await this.getAuthHeaders()
    } catch {
      // Continue without auth headers
    }
    
    return this.request<QueryHistoryItem[]>('/api/queries', {
      headers,
      params: {
        limit,
        offset,
      },
      next: {
        revalidate: 60, // 1 minute cache for query history
        tags: ['queries']
      }
    })
  }

  async getQuery(queryId: string): Promise<QueryResponse> {
    // Try to get auth headers, but don't fail if not authenticated
    let headers = {}
    try {
      headers = await this.getAuthHeaders()
    } catch {
      // Continue without auth headers
    }
    
    return this.request<QueryResponse>(`/api/queries/${queryId}`, {
      headers,
      next: {
        revalidate: 3600, // 1 hour cache for individual queries
        tags: [`query-${queryId}`, 'queries']
      }
    })
  }

  // Checklist Analysis methods
  async createChecklistAnalysis(request: ChecklistAnalysisRequest): Promise<ChecklistAnalysisResponse> {
    // Try to get auth headers, but don't fail if not authenticated (public projects)
    let headers = {}
    try {
      headers = await this.getAuthHeaders()
    } catch {
      // Continue without auth headers for public projects
    }
    
    return this.request<ChecklistAnalysisResponse>('/api/checklist/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    })
  }

  async getChecklistAnalysisRun(runId: string): Promise<ChecklistAnalysisRun> {
    // Try to get auth headers, but don't fail if not authenticated
    let headers = {}
    try {
      headers = await this.getAuthHeaders()
    } catch {
      // Continue without auth headers
    }
    
    return this.request<ChecklistAnalysisRun>(`/api/checklist/runs/${runId}`, {
      headers,
    })
  }

  async getChecklistAnalysisRuns(indexingRunId: string): Promise<ChecklistAnalysisRun[]> {
    // Try to get auth headers, but don't fail if not authenticated
    let headers = {}
    try {
      headers = await this.getAuthHeaders()
    } catch {
      // Continue without auth headers
    }
    
    return this.request<ChecklistAnalysisRun[]>('/api/checklist/runs', {
      headers,
      params: {
        indexing_run_id: indexingRunId,
      },
      next: {
        revalidate: 300, // 5 minutes cache for analysis runs
        tags: [`checklist-runs-${indexingRunId}`, 'checklist-runs']
      }
    })
  }
}

export const apiClient = new ApiClient()