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
    options?: RequestInit & { params?: Record<string, unknown> }
  ): Promise<T> {
    const url = new URL(endpoint, this.baseURL)
    
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }

    const response = await fetch(url.toString(), {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

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
    return this.request<any[]>(`/api/indexing-runs-with-wikis?limit=${limit}`);
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
    return this.request<{pages: WikiPage[], total_pages: number}>(`/api/wiki/runs/${wikiRunId}/pages`)
  }

  async getWikiPageContent(wikiRunId: string, pageName: string): Promise<WikiPageContent> {
    return this.request<WikiPageContent>(`/api/wiki/runs/${wikiRunId}/pages/${pageName}`)
  }

  async getWikiMetadata(wikiRunId: string): Promise<WikiMetadata> {
    return this.request<WikiMetadata>(`/api/wiki/runs/${wikiRunId}/metadata`)
  }

  async getWikiRunStatus(wikiRunId: string): Promise<WikiRunStatus> {
    return this.request<WikiRunStatus>(`/api/wiki/runs/${wikiRunId}/status`)
  }

  async getWikiRunsByIndexingRun(indexingRunId: string): Promise<WikiRun[]> {
    return this.request<WikiRun[]>(`/api/wiki/runs/${indexingRunId}`)
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
    return this.request<ProjectDetails>(`/api/indexing-runs/${projectId}`)
  }
}

export const apiClient = new ApiClient()