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
  id: string
  indexing_run_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  pages_count: number
  total_word_count: number
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
    add_context_headers?: boolean
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

export class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL!
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    
    return session?.access_token 
      ? { Authorization: `Bearer ${session.access_token}` }
      : {}
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
    return this.request<{pages: WikiPage[], total_pages: number}>(`/api/wiki/runs/${wikiRunId}/pages`, {
      next: {
        revalidate: 3600, // 1 hour cache for wiki pages list
        tags: [`wiki-pages-${wikiRunId}`, 'wiki-pages']
      }
    })
  }

  async getWikiPageContent(wikiRunId: string, pageName: string): Promise<WikiPageContent> {
    return this.request<WikiPageContent>(`/api/wiki/runs/${wikiRunId}/pages/${pageName}`, {
      next: {
        revalidate: 3600, // 1 hour cache for wiki page content
        tags: [`wiki-content-${wikiRunId}-${pageName}`, 'wiki-content']
      }
    })
  }

  async getWikiMetadata(wikiRunId: string): Promise<WikiMetadata> {
    return this.request<WikiMetadata>(`/api/wiki/runs/${wikiRunId}/metadata`)
  }

  async getWikiRunStatus(wikiRunId: string): Promise<WikiRunStatus> {
    return this.request<WikiRunStatus>(`/api/wiki/runs/${wikiRunId}/status`)
  }

  async getWikiRunsByIndexingRun(indexingRunId: string): Promise<WikiRun[]> {
    return this.request<WikiRun[]>(`/api/wiki/runs/${indexingRunId}`, {
      next: {
        revalidate: 3600, // 1 hour cache for wiki runs
        tags: [`wiki-runs-${indexingRunId}`, 'wiki-runs']
      }
    })
  }

  // Project-related methods
  async getProjectFromSlug(slug: string): Promise<ProjectDetails> {
    // Extract UUID from slug (format: "project-name-uuid")
    // UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (8-4-4-4-12 = 36 chars with dashes)
    const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const match = slug.match(uuidRegex);
    
    if (!match) {
      throw new Error(`Invalid project slug format: ${slug}`);
    }
    
    const projectId = match[0];
    return this.request<ProjectDetails>(`/api/indexing-runs/${projectId}`, {
      next: {
        revalidate: 3600, // 1 hour cache for project details
        tags: [`project-${projectId}`, 'indexing-runs']
      }
    })
  }

  async getIndexingRunWithConfig(slug: string): Promise<IndexingRunWithConfig> {
    // Extract UUID from slug (format: "project-name-uuid")
    const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const match = slug.match(uuidRegex);
    
    if (!match) {
      throw new Error(`Invalid project slug format: ${slug}`);
    }
    
    const projectId = match[0];
    return this.request<IndexingRunWithConfig>(`/api/indexing-runs/${projectId}`, {
      next: {
        revalidate: 3600, // 1 hour cache for indexing run details
        tags: [`indexing-run-config-${projectId}`, 'indexing-runs']
      }
    })
  }

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
}

export const apiClient = new ApiClient()